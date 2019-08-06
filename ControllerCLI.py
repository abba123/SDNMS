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

def get_host():
    response = requests.get("http://127.0.0.1:8080/switch/host")
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
    host=get_host()
    command=[]

    def do_flows(self,line):
        """Command: flows [s1]\nDescription: Show s1 flow entry"""
        switch=line
        if switch:
            if switch in Shell.switch_map:
                response = requests.get("http://127.0.0.1:8080/switch/flowtable/"+Shell.switch_map[switch])
                print(json.dumps(response.json(), indent=4, sort_keys=True))
            else:
                print "can not find the switch"
        else:
            print """Command: flows [s1]\ndescription: Show s1 flow entry"""
    
    def do_switch(self,line):
        """Command: switch [s1]\nDescription: Show switchs description"""
        switch=line
        if switch:
            if switch in Shell.switch_map:
                response = requests.get("http://127.0.0.1:8080/switch/switch/"+Shell.switch_map[switch])
                print(json.dumps(response.json(), indent=4, sort_keys=True))
            else:
                print "can not find the switch"
        else:
            Shell.switch_map=get_switch()
            print(json.dumps(Shell.switch_map.keys(), indent=4, sort_keys=True))
    
    def do_port(self,line):
        """Command: port [s1] [1]\nDescription: Show ports description"""
        if line:
            line=line.split()
            if len(line) ==2:
                switch = line[0]
                port = line[1]
                if switch not in Shell.switch_map:
                    print "can not find the switch"
                elif port not in Shell.port_map[switch]:
                    print "can not find the port"
                else:
                    response = requests.get("http://127.0.0.1:8080/switch/port/"+Shell.switch_map[switch]+"/"+port)
                    print(json.dumps(response.json(), indent=4, sort_keys=True))
            else:
                print "Command: port [s1] [1]\nDescription: show ports description"
        else:
            Shell.port_map=get_port()
            print(json.dumps(Shell.port_map, indent=4, sort_keys=True))

    def do_firewall(self,line):
        """Command: firewall [add/delete] [s1] [in_port=1] [eth_type=0x0800] [src_ip=10.0.0.1] [src_mac=00:00:00:00:00:00] [dst_ip=10.0.0.1] [dst_mac=00:00:00:00:00:00]\nDescription: Set firewall"""
        if line:
            line=line.split()
            if line[1] in Shell.switch_map:
                flow={}
                error=0
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
                        error=1
                        break
                if error==0:
                    if line[0]=="add":
                        response = requests.post("http://127.0.0.1:8080/switch/flowtable/"+Shell.switch_map[line[1]],data=json.dumps(flow))
                    elif line[0]=="delete":
                        response = requests.delete("http://127.0.0.1:8080/switch/flowtable/"+Shell.switch_map[line[1]],data=json.dumps(flow))
            else:
                print "can not find the switch"
        else:
            print """Command: firewall [add/delete] [s1] [in_port=1] [eth_type=0x0800] [src_ip=10.0.0.1] [src_mac=00:00:00:00:00:00] [dst_ip=10.0.0.1] [dst_mac=00:00:00:00:00:00]\nDescription: Set firewall"""

    def do_link(self,line):
        """Command: link\nDescription: Show the link"""
        Shell.link=get_link()
        for switch1 in Shell.link:
            for x in Shell.link[switch1]:
                for port1 in x:
                    print "(s"+switch1+",p"+port1+") --- (s"+x[port1][0]+",p"+x[port1][1]+")"
        Shell.host=get_host()
        for h in Shell.host:
            print "("+h+") --- (s" + str(Shell.host[h]["switch"])+",p"+str(Shell.host[h]["port"])+")"
    def do_topo(self,line):
        """Command: topo\nDescription: Create the topo"""
        G = nx.Graph()
        edge_labels={}

        plt.figure(figsize=(10,10))
        
        for switch in Shell.switch_map:
            G.add_node(switch)
        
        for eth in Shell.host:
            G.add_node(eth)

        for switch1 in Shell.link:
            for x in Shell.link[switch1]:
                for port1 in x:
                    G.add_edge("s"+switch1,"s"+x[port1][0])
                    edge_labels["s"+switch1,"s"+x[port1][0]]= "(s"+switch1+","+port1+") --- (s"+x[port1][0]+","+x[port1][1]+")"
        
        for eth in Shell.host:
            G.add_edge(eth,"s"+str(Shell.host[eth]["switch"]))
            edge_labels[eth,"s"+str(Shell.host[eth]["switch"])]= "("+eth+") --- (s"+str(Shell.host[eth]["switch"])+","+str(Shell.host[eth]["port"])+")"
        
        pos=nx.spring_layout(G)
        nx.draw(G,with_labels=True,pos=pos)
        #nx.draw_networkx_edge_labels(G,pos=pos,edge_labels=edge_labels)
        plt.draw()
        plt.savefig('topo.png')

    def do_host(self,line):
        """Command: host\nDescription: Show host"""
        Shell.host=get_host()
        print(json.dumps(Shell.host, indent=4, sort_keys=True))

    def do_history(self,line):
        """Command: history\nDescription: Show history command"""
        count=0
        for cmd in Shell.command:
            print count,cmd
            count+=1
    
    def do_saveflow(self,line):
        """Command: saveflow [s1] [filename]\nDescription: Save switch flow entry"""
        line=line.split()
        if len(line) >= 2:
            switch=line[0]
            if switch in Shell.switch_map:
                filename=line[1]
                response = requests.post("http://127.0.0.1:8080/switch/saveflow/"+Shell.switch_map[switch],data=filename)
            else:
                print "can not find the switch"
        else:
            print "Command: savefile [s1] [filename]\nDescription: Save switch flow entry"
    
    def do_loadflow(self,line):
        """Command: loadflow [s1] [filename]\nDescription: Load switch flow entry"""
        line=line.split()
        if len(line) >= 2:
            switch=line[0]
            if switch in Shell.switch_map:
                filename=line[1]
                response = requests.post("http://127.0.0.1:8080/switch/loadflow/"+Shell.switch_map[switch],data=filename)
            else:
                print "can not find the switch"
        else:
            print """Command: loadflow [s1] [filename]\nDescription: Load switch flow entry"""

    def do_exit(self,line):
        """exit\nexit the command"""
        return True
     
    def emptyline(self):
         pass
    
    def precmd(self, line):
        line = line.lower()
        Shell.command.append(line)
        return line

if __name__ == '__main__':
    Shell().cmdloop()
