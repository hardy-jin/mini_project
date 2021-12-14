"""
This is where the implementation of the plugin code goes.
The ReachCheck-class is imported from both run_plugin.py and run_debug.py
"""
import sys
import logging
from webgme_bindings import PluginBase

# Setup a logger
logger = logging.getLogger('ReachCheck')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)  # By default it logs to stderr..
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class ReachCheck(PluginBase):
    def main(self):
        core = self.core
        root_node = self.root_node
        META = self.META
        active_node = self.active_node # we assume the active node is the state machine node

        visited = set()
        states = set()
        places = []
        tracks = []
        entry = []
        exit_ls = []
        connections = []
        graph_elem = {}
        graph = {}
        # we build the most simple graph representation possible
        nodes = core.load_children(active_node)
        for node in nodes:
            if core.is_type_of(node, META['Station']):
                states.add(core.get_path(node))
            if core.is_type_of(node, META['Station']):
                visited.add(core.get_path(node))
        for node in nodes:
            if core.is_type_of(node, META['Transition']):
                if core.get_pointer_path(node, 'src') in graph:
                    graph[core.get_pointer_path(node, 'src')].append(core.get_pointer_path(node, 'dst'))
                else:
                    graph[core.get_pointer_path(node, 'src')] = [core.get_pointer_path(node, 'dst')]
        
        # now we just update the visited set
        old_size = len(visited)
        new_size = 0

        while old_size != new_size:
            old_size = len(visited)
            elements = list(visited)
            for element in elements:
                if element in graph:
                    for next_state in graph[element]:
                        visited.add(next_state)
            new_size = len(visited)
        
        # now we just simply check if we have a difference between the foll set of states and the reachable ones
        if len(states.difference(visited)) == 0:
            # everything is fine
            self.send_notification('Your state machine is well formed')
        else:
            # we need some states that are unreachable
            self.send_notification('Your state machine has unreachable states')
        
        node_ls = core.load_sub_tree(active_node)
        for node in node_ls:
            if core.get_path(node):
                graph_elem[core.get_path(node)] = core.get_attribute(node, 'name')

        for node in node_ls:
            if core.is_type_of(node, META['Station']):
                places.append(core.get_attribute(node, 'name'))
            elif core.is_type_of(node, META['Transition']):
                tracks.append(core.get_attribute(node, 'name'))
            elif core.is_type_of(node, META['Entry']):
                src_id = core.get_pointer_path(node, 'src')
                dst_val = core.get_pointer_path(node, 'dst')
                input_val = {'name': core.get_attribute(
                    node, 'name'), 'src': graph_elem.get(src_id), 'dst': graph_elem.get(dst_val)}
                connections.append((graph_elem.get(src_id), graph_elem.get(dst_val)))
                entry.append(input_val)
            elif core.is_type_of(node, META['Exit']):
                src_id = core.get_pointer_path(node, 'src')
                dst_val = core.get_pointer_path(node, 'dst')
                output_val = {'name': core.get_attribute(
                    node, 'name'), 'src': graph_elem.get(src_id), 'dst': graph_elem.get(dst_val)}
                connections.append((graph_elem.get(src_id), graph_elem.get(dst_val)))
                exit_ls.append(output_val)


        order = []
        check_val = set()

        def dfs(check_val, graph, node):
            if node not in check_val:
                order.append(node)
                check_val.add(node)
                for neighbour in graph[node]:
                    dfs(check_val, graph, neighbour)

        def dfs_paths(graph, start, goal):
            stack = [(start, [start])]
            while stack:
                (vertex, path) = stack.pop()
                for next in graph[vertex] - set(path):
                    if next == goal:
                        yield path + [next]
                    else:
                        stack.append((next, path + [next]))
                        
        def checkPlace(places,tracks):
            check_ls = []
            for i in places:
                if i['src'] in tracks:
                    if i['src'] not in check_ls:
                        check_ls.append(i['src'])  
                if i['dst'] in tracks:
                    if i['dst'] not in check_ls:
                        check_ls.append(i['dst'])
            return check_ls
                    
        in_place = checkPlace(entry, tracks)
        out_place = checkPlace(exit_ls, tracks)

        if in_place == out_place:
            self.send_notification('Your Marked Graph is well formed')
        else:
            # we need some states that are unreachable
            self.send_notification('Your Marked Graph has unreachable states')
        def freeChoice(entry):
            count = 0
            for inplace in entry:
                for temp in entry:
                    if inplace == temp:
                        count += 1
            return count == len(entry)

        if freeChoice(entry):
            self.send_notification('Your Free Choice is well formed')
        else:
            # we need some states that are unreachable
            self.send_notification('Your Free Choice has unreachable states')
        
        def workFlow(places, tracks, connections, in_place, out_place):
            counter = 0
            set_ls = []
            temp = []
            w_data = []
            s_value = None
            s_counter = 0
            d_value = None
            d_counter = 0
            for place in places:
                w_data.append(place)
            for transition in tracks:
                w_data.append(transition)
            for place in places:
                if place not in out_place and place in in_place:
                    if s_counter != 0:
                        return False
                    else:
                        s_value = place
                        s_counter += 1   
                if place not in in_place and place in out_place:
                    if d_counter != 0:
                        return False
                    else:
                        d_value = place
                        d_counter += 1    
            temp.append(s_value)
            set_ls.append(d_value)
            checker = False
            while len(w_data) > counter:
                if len(temp) == 0:
                    return False
                current = temp.pop()
                counter += 1
                if current == d_value:
                    checker = True
                for i in connections:
                    if i[0] == current:
                        if i[1] not in set_ls:
                            set_ls.append(i[1])
                            temp.append(i[1])
            for j in w_data:
                if j not in set_ls:
                     return False
            return checker
        flag = workFlow(places, tracks, connections, in_place, out_place)
        if flag:
            self.send_notification('Your Workflow Net is well formed')
        else:
            # we need some states that are unreachable
            self.send_notification('Your Workflow Net has unreachable states')
