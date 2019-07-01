import requests
import json
import cmd
import networkx as nx
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

def get_port():
    port_map={}
    response = requests.get("http://127.0.0.1:8080/switch/portID")
    for switch in response.json():
        port_map["s"+switch]=response.json()[switch].keys()
    return port_map

def get_switch():
    switch_map={}
    response = requests.get("http://127.0.0.1:8080/switch/switchDPID")
    
    for switch in response.json():
        switch_map['s'+str(switch)]=str(switch)
    return switch_map

def get_link():
    response = requests.get("http://127.0.0.1:8080/switch/link")
    return response.json()

def set_intro(switch_map):
    intro='\nWelcome to command line\n\n'+'your switch :\n'
    for switch in switch_map:
        intro+=switch
        intro+=" "
    intro+="\n"
    return intro

class Shell(cmd.Cmd):
    
    prompt = '>'

    switch_map=get_switch()
    port_map=get_port() 
    intro=set_intro(switch_map)
    link=get_link()

    def do_flows(self,switch):
        """flows [s1]\nShow s1 flow entry"""
        if switch:
            if switch in Shell.switch_map:
                response = requests.get("http://127.0.0.1:8080/switch/flowtable/"+Shell.switch_map[switch])
                print(json.dumps(response.json(), indent=4, sort_keys=True))
            else:
                print "can not find the switch"
        else:
            print """flows [s1]\nShow s1 flow entry"""
    
    def do_switch(self,switch):
        """switch [s1]\nShow switchs description"""
        if switch:
            if switch in Shell.switch_map:
                response = requests.get("http://127.0.0.1:8080/switch/switch/"+Shell.switch_map[switch])
                print(json.dumps(response.json(), indent=4, sort_keys=True))
            else:
                print "can not find the switch"
        else:
            Shell.switch_map=get_switch()
            print(json.dumps(Shell.switch_map.keys(), indent=4, sort_keys=True))
    
    def do_port(self,arg):
        """port [s1] [1]\nShow ports description"""
        if arg:
            arg=arg.split()
            if len(arg) ==2:
                switch = arg[0]
                port = arg[1]
                if switch not in Shell.switch_map:
                    print "can not find the switch"
                elif port not in Shell.port_map[switch]:
                    print "can not find the port"
                else:
                    response = requests.get("http://127.0.0.1:8080/switch/port/"+Shell.switch_map[switch]+"/"+port)
                    print(json.dumps(response.json(), indent=4, sort_keys=True))
            else:
                print "port [s1] [1]\nshow ports description"
        else:
            Shell.port_map=get_port()
            print(json.dumps(Shell.port_map, indent=4, sort_keys=True))

    def do_firewall(self,line):
        """ firewall [deny/delete] [s1] [in_port=1] [eth_type=0x0800] [src_ip=10.0.0.1] [src_mac=00:00:00:00:00:00] [dst_ip=10.0.0.1] [dst_mac=00:00:00:00:00:00]\nSet firewall"""
        if line:
            line=line.split()
            if line[1] in Shell.switch_map:
                flow={}
                par_error=0
                flow['action']=line[0]
                for par in line[2:]:
                    tmp=par.split("=")
                    if tmp[0]=='in_port':
                        flow['in_port']=tmp[1]
                    elif tmp[0]=='eth_type':
                        flow['eth_type']=tmp[1]
                    elif tmp[0]=='src_ip':
                        flow['ipv4_src']=tmp[1]
                    elif tmp[0]=='src_mac':
                        flow['eth_src']=tmp[1]
                    elif tmp[0]=='dst_ip':
                        flow['ipv4_dst']=tmp[1]
                    elif tmp[0]=='dst_mac':
                        flow['eth_dst']=tmp[1]
                    else:
                        print "parameter error : "+tmp[0]
                        error_flag=1
                        break
                if par_error==0:
                    response = requests.put("http://127.0.0.1:8080/switch/flowtable/"+Shell.switch_map[line[1]],data=json.dumps(flow))
            else:
                print "can not find the switch"
        else:
            print """ firewall [deny/delete] [s1] [in_port=1] [eth_type=0x0800] [src_ip=10.0.0.1] [src_mac=00:00:00:00:00:00] [dst_ip=10.0.0.1] [dst_mac=00:00:00:00:00:00]\nSet firewall"""

    def do_link(self,line):
        """link\nShow the link"""
        Shell.link=get_link()
        for switch1 in Shell.link:
            for x in Shell.link[switch1]:
                for port1 in x:
                    print "(s"+switch1+","+port1+") --- (s"+x[port1][0]+","+x[port1][1]+")"
    
    def do_topo(self,line):
        """topo\nShow the topo"""
        G = nx.Graph()
        edge_labels={}
        for switch in Shell.switch_map:
            G.add_node(switch,label=switch)
        for switch1 in Shell.link:
            for x in Shell.link[switch1]:
                for port1 in x:
                    G.add_edge("s"+switch1,"s"+x[port1][0])
                    edge_labels["s"+switch1,"s"+x[port1][0]]= "(s"+switch1+","+port1+") --- (s"+x[port1][0]+","+x[port1][1]+")"
        nx.draw(G,with_labels=True,pos=nx.spectral_layout(G))
        nx.draw_networkx_edge_labels(G,pos=nx.spectral_layout(G),edge_labels=edge_labels)
        plt.draw()
        plt.savefig('topo.png')
    def do_exit(self,line):
        """exit\nexit the command"""
        return True
     
    def emptyline(self):
         pass
if __name__ == '__main__':
    Shell().cmdloop()
