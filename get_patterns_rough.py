#coding: utf-8
import copy

# algorithm:
# 1. split url to pieces 
# 2. generate tree
# 3. rebuild rule, print

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
    hosts = ['%s_%s' % (i, v) for i, v in enumerate(hosts) if v]
    paths = ['/%s_%s' % (i, v) for i, v in enumerate(path_arr[1:]) if v] 
    args = url.split('?', 1)[-1].split('&') if url.count('?') >= 1 else []
    args = ['?%s=$$' % v.split('=')[0] for v in args if v]
    return (hosts + paths + args)

class TreeNode(object):
    def __init__(self):
        self.children = []
        self.data = []
        self.rule = ''
        self.available = True
        self.tot_num = 0
        self.sample = [] 

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
    while len(node.data) >= n_tot * g_min_node_rate:
        feat_stat = {}
        for arr in node.data:
            for feat in arr:
                feat_stat[feat] = feat_stat.get(feat, 0) + 1
        sort_list = sorted(feat_stat.items(), key=lambda d:-d[1])
        if not sort_list: 
            break
        feat, imp = sort_list[0]
        if imp >= g_min_node_imp and imp >= n_tot * g_min_node_rate: 
            new_node = TreeNode() 
            new_node.rule = feat
            node.children.append(new_node)
            #remove rule from matched arr, move arr to new_node
            old_data = node.data
            node.data = []
            for arr in old_data:
                if feat in arr:
                    arr.remove(feat)
                    new_node.data.append(arr)
                else:
                    node.data.append(arr)
            new_node.tot_num = len(new_node.data)
            new_node.sample = copy.deepcopy(new_node.data[0])
            #print 'add rule, cur: %s, child: %s' % (node.rule, new_node.rule)
        else: 
            break
    node.available = False

def generate_tree(url_set):
    root = TreeNode() 
    for url in url_set:
        arr = split_url(url)
        root.data.append(arr)

    for node in travel_available(root):
        process_node(node) 
        node.available = False
    return root

##############

def rebuild_url(pieces, sample, is_sample=False):
    max_host_idx, max_path_idx = 0, 0
    for v in sample:
        if not v: continue
        if   v[0] == '?': continue 
        elif v[0] == '/': max_path_idx = max(int(v[1:].split('_')[0]), max_path_idx)
        else:             max_host_idx = max(int(v.split('_')[0]), max_host_idx)
    #print max_host_idx, max_path_idx

    to_rebuild = pieces+sample if is_sample else pieces
    hosts, paths, args = [], [], []
    for v in to_rebuild:
        if not v: continue
        if   v[0] == '?': args.append(v[1:])
        elif v[0] == '/': paths.append((int(v[1:].split('_')[0]), v.split('_',1)[1]))
        else:             hosts.append((int(v.split('_')[0]), v.split('_',1)[1]))
    sort_host = sorted(hosts, key=lambda d:-d[0])
    all_host = []
    for i, pair in enumerate(sort_host):
        idx, s = pair
        if i==0 and max_host_idx > idx:
            all_host += ['*'] * 1 #(max_host_idx-idx)
        elif i>0:
            all_host += ['*'] * (sort_host[i-1][0]-idx-1)
        all_host.append(s)
        if i==len(sort_host)-1 and idx > 0:
            all_host += ['*'] * (idx)
    if not sort_host and max_host_idx > 0:
        all_host += ['*'] * 1 #max_host_idx

    sort_path = sorted(paths, key=lambda d:d[0]) 
    all_path = []
    for i, pair in enumerate(sort_path): 
        idx, s = pair
        if i==0 and idx > 0:
            all_path += ['*'] * (idx)
        elif i>0:
            all_path += ['*'] * (idx-sort_path[i-1][0]-1)
        all_path.append(s)
        if i==len(sort_path)-1 and max_path_idx > idx:
            all_path += ['*'] * 1 #(max_path_idx-idx)
    if not sort_path and max_path_idx > 0:
        all_path += ['*'] * 1 #max_path_idx

    if args:
        return '%s/%s?%s' % ('.'.join(all_host), '/'.join(all_path), '&'.join(sorted(args)))
    else:
        return '%s/%s' % ('.'.join(all_host), '/'.join(all_path))

def travel_rules(node, pre_path=[], only_leaf=True, threshold=100):
    new_path = pre_path + [node.rule]
    if not node.children and node.tot_num >= threshold:
        yield new_path, node.tot_num, node.sample
    elif not only_leaf and node.tot_num >= threshold:
        yield new_path, node.tot_num, node.sample
    for child in node.children:
        for pattern, imp, sample in travel_rules(child, new_path, only_leaf, threshold):
            yield pattern, imp, sample 

def print_all_patterns(root_node, only_leaf=True, threshold=100):
    candidates = []
    for pattern, imp, sample in travel_rules(root_node, pre_path=[], only_leaf=only_leaf, threshold=threshold): 
        candidates.append( (pattern, imp, sample) )
    sort_list = sorted(candidates, key=lambda d:-d[1])
    for pattern, imp, sample in sort_list:
        ret = {}
        #ret['pieces'] = pattern
        ret['pattern'] = rebuild_url(pattern, sample, is_sample=False)
        ret['count'] = imp
        ret['sample'] = rebuild_url(pattern, sample, is_sample=True)
        ret['level'] = len(pattern)
        print ret

##############

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
    url = 'http://hz.58.com/zufang/j2/?keywordid=3882774738&ideaid=914411255&utm_source=baidu-sem&utm_campaign=sell&utm_medium=cpc'
    print url
    print split_url(url)


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == 'test':
        test()
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print '<usage> p_url'

