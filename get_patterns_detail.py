#coding: utf-8

# algorithm:
# 1. depack url to host, path, arg; spread to (key, value)
# 2. greedy grow
# 3. stat key's entropy

g_min_node_imp = 100
g_min_node_rate = 0.001

def get_url_set(p_in):
    url_set = set()
    for line in open(p_in):
        url = line.strip().split('\t')[-1]
        url_set.add(url)
    return url_set


def split_url(url):
    url = url.split('//', 1)[-1]
    path_arr = url.split('?', 1)[0].split('#')[0].split('/')
    hosts = path_arr[0].split('.')
    hosts.reverse()
    paths = path_arr[1:]
    args = url.split('?', 1)[-1].split('&') if url.count('?') >= 1 else []

    results = []
    for i, v in enumerate(hosts):
        if not v: continue
        parts = v.split('-')
        for i2 in range(0, len(parts)+1):
            results.append( 'host:%d:%d=%s' % (i, i2, '-'.join(parts[:i2] + ['$$']*(len(parts)-i2))) )
    for i, v in enumerate(paths):
        if not v: continue
        parts = v.split('-')
        for i2 in range(0, len(parts)+1):
            results.append( 'path:%d:%d=%s' % (i, i2, '-'.join(parts[:i2] + ['$$']*(len(parts)-i2))) )
    for v0 in args:
        if not v0 or v0.count('=') != 1: continue
        k, v = v0.split('=')
        parts = v.split('-')
        for i2 in range(0, len(parts)+1):
            results.append( 'arg:%s:%d=%s' % (k, i2, '-'.join(parts[:i2] + ['$$']*(len(parts)-i2))) )
    return results 


class TreeNode(object):
    def __init__(self):
        self.children = []
        self.data = []
        self.rule = ''
        self.num = 0
        self.available = True

def travel_available(root):
    queue = [root] 
    while queue:
        node = queue.pop()
        if node.available:
            yield node
        queue.extend( node.children )

def process_node(node):
    # greedy stategy
    n_tot = len(node.data)
    while True: 
        feat_stat = {}
        for arr in node.data:
            for feat in arr:
                feat_stat[feat] = feat_stat.get(feat, 0) + 1
        if not feat_stat: break
        for feat in feat_stat:
            t, i, r = feat.split('=')[0].split(':',2)
            if   t == 'host': feat_stat[feat] += 0.6 - int(i) * 0.01
            elif t == 'path': feat_stat[feat] += 0.3 - int(i) * 0.01
        # find best feature
        sort_list = sorted(feat_stat.items(), key=lambda d:-d[1])
        feat, imp = sort_list[0]
        if imp >= g_min_node_imp and imp >= n_tot * g_min_node_rate: 
            new_node = TreeNode() 
            new_node.rule = feat
            #remove rule from arr, move arr to new_node
            old_data = node.data
            node.data = []
            for arr in old_data:
                if feat in arr:
                    arr.remove(feat)
                    new_node.data.append(arr)
                else:
                    node.data.append(arr)
            new_node.num = len(new_node.data)
            node.children.append(new_node)
            #print 'add rule, cur: %s, child: %s, num: %d' % (node.rule, new_node.rule, new_node.num)
        else: 
            break
    node.available = False

def generate_tree(url_set):
    root = TreeNode() 
    tlds = set()
    for url in url_set:
        arr = split_url(url)
        if 'host:0:0=$$' in arr:
            arr.remove('host:0:0=$$') 
        root.data.append(arr)
        for v in arr:
            if v.startswith('host:0:1='):
                tlds.add(v)
    for tld in tlds:
        new_node = TreeNode()
        new_node.rule = tld
        for arr in root.data:
            if tld in arr:
                arr.remove(tld)
                new_node.data.append(arr)
        new_node.num = len(new_node.data)
        root.children.append(new_node)
    root.data = []
    root.available = False
    # get rules
    for child in root.children:
        for node in travel_available(child):
            process_node(node) 
            node.available = False
    return root


def rebuild_url(part_arr, node_num, node_data):
    hosts, paths, args = {}, {}, {} 
    for part in part_arr:
        if part.count('=') < 1: continue 
        part_key, part_v = part.split('=', 1)
        t, i, r = part_key.split(':')
        i = int(i) if i.isdigit() else i
        r = int(r)
        if   t == 'host' and r > hosts.get(i, (-1, '*'))[0]: hosts[i] = (r, part_v)
        elif t == 'path' and r > paths.get(i, (-1, '*'))[0]: paths[i] = (r, part_v)
        elif t == 'arg'  and r > args.get(i, (-1, '*'))[0]: args[i] = (r, part_v)

    max_host_idx = max(hosts.keys() + [-1])
    all_hosts = []
    for i in range(max_host_idx+1):
        all_hosts.append(hosts.get(i, (0, '*'))[1])
    all_hosts.reverse()
    max_path_idx = max(paths.keys() + [-1])
    all_paths = []
    for i in range(max_path_idx+1):
        all_paths.append(paths.get(i, (0, '*'))[1])
    all_args = []
    for i in args:
        all_args.append('%s=%s' % (i, args[i][1]))

    if all_args:
        return '%s/%s?%s' % ('.'.join(all_hosts), '/'.join(all_paths), '&'.join(sorted(all_args)))
    else:
        return '%s/%s' % ('.'.join(all_hosts), '/'.join(all_paths))

def travel_rules(node, pre_path=[], only_leaf=True, threshold=100):
    new_path = pre_path + [node.rule]
    if not node.children:
        yield rebuild_url(new_path, node.num, node.data), node.num, rebuild_url(new_path+node.data[0], node.num, []) 
    for child in node.children:
        for pattern, imp, sample in travel_rules(child, new_path, only_leaf, threshold):
            yield pattern, imp, sample

def print_all_patterns(root_node, only_leaf=True, threshold=100):
    candidates = []
    for child in root_node.children:
        for pattern, imp, sample in travel_rules(root_node, pre_path=[], only_leaf=only_leaf, threshold=threshold): 
            candidates.append( (pattern, imp, sample) )
    sort_list = sorted(candidates, key=lambda d:-d[1])
    for pattern, imp, sample in sort_list:
        ret = {}
        ret['pattern'] = pattern
        ret['count'] = imp
        ret['sample'] = sample 
        print ret


def main(p_in):
    #print 'main'.center(20, '*')
    url_set = get_url_set(p_in)
    #print 'get url set finished, len:', len(url_set)
    root = generate_tree(url_set)
    #print 'generate tree finished'
    print_all_patterns(root, only_leaf=False, threshold=1000)
    #print 'print tree finished'

def test():
    print 'test'.center(20, '*')
    urls = ['http://hz.58.com/zufang/j2/?keywordid=3882774738&ideaid=914411255&utm_source=baidu-sem&utm_campaign=sell&utm_medium=cpc',
            'http://ju.suning.com/product-00a40146b042d465.htm',
            ]
    for url in urls:
        print 'url:', url 
        print split_url(url)


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == 'test':
        test()
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print '<usage> p_url'

