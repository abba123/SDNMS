# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import lldp

from webob import Response
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib import dpid as dpid_lib

import copy
import json
import time
simple_switch_instance_name = 'simple_switch_api_app'
url = '/switch/'
class mySwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    _CONTEXTS = { 'wsgi': WSGIApplication }

    def __init__(self, *args, **kwargs):

        super(mySwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}   #mac_to_port[dpid][src] : in_port
        wsgi = kwargs['wsgi']
        wsgi.register(SimpleSwitchController, {simple_switch_instance_name : self})
        self.datapaths={}   #datapaths[dpid] : datapath
        self.flow_table={}  #flow_table[dpid] : flows
        self.switch={}      #switch[dpdi] : switch_features
        self.port={}        #port[dpid][port] : port_desc_stats
        self.link={}        #link[switch][port] : switch,port

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[str(datapath.id)]=datapath
        tmp={}
        msg=ev.msg
        tmp["datapath_id"]=msg.datapath_id
        tmp["n_buffers"]=msg.n_buffers
        tmp["n_tables"]=msg.n_tables
        tmp["auxiliary_id"]=msg.auxiliary_id
        tmp["capabilities"]=msg.capabilities
        self.switch[str(datapath.id)]=tmp
        
        self.send_port_desc_stats_request(datapath)
        
        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_LLDP)
        actions = [parser.OFPActionOutput(port=ofproto.OFPP_CONTROLLER, max_len=ofproto.OFPCML_NO_BUFFER)]

        self.add_flow(datapath, 0, match, actions)
    
    def link_discovery(self):

        for dpid in self.datapaths:
            for port in self.port[dpid]:
                if port != "4294967294":
                    self.send_lldp(self.datapaths[dpid],int(port),self.port[dpid][port]["hw_addr"])

    def send_lldp(self, datapath, port_no, hw_addr):
        ofp=datapath.ofproto
        pkt=packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_LLDP, src=hw_addr, dst=lldp.LLDP_MAC_NEAREST_BRIDGE))

        tlv_chassis_id = lldp.ChassisID(subtype=lldp.ChassisID.SUB_LOCALLY_ASSIGNED, chassis_id=str(datapath.id))
        tlv_port_id = lldp.PortID(subtype=lldp.PortID.SUB_LOCALLY_ASSIGNED, port_id=str(port_no))
        tlv_ttl = lldp.TTL(ttl=10)
        tlv_end = lldp.End()
        tlvs = (tlv_chassis_id, tlv_port_id, tlv_ttl, tlv_end)
        pkt.add_protocol(lldp.lldp(tlvs))
        pkt.serialize()

        data = pkt.data
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(port=port_no)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofp.OFP_NO_BUFFER, in_port=ofp.OFPP_CONTROLLER, actions=actions, data=data)
        
        datapath.send_msg(out)
   
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def del_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        cookie = cookie_mask = 0
        table_id = 0
        idle_timeout = hard_timeout = 0
        buffer_id = ofproto.OFP_NO_BUFFER
        actions = []
        inst = []
        req = parser.OFPFlowMod(datapath, match= match, command=ofproto.OFPFC_DELETE, out_port=ofproto.OFPG_ANY,out_group=ofproto.OFPG_ANY)
        
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            pkt=pkt.get_protocol(lldp.lldp)
            lldp_switchID=pkt.tlvs[0].chassis_id
            lldp_portID=pkt.tlvs[1].port_id
            if datapath.id > int(lldp_switchID):
                if lldp_switchID not in self.link:
                    self.link[lldp_switchID]=[]
            
                tmp={lldp_portID:[str(datapath.id), str(in_port)]}
                self.link[lldp_switchID].append(tmp)
                print "(",lldp_switchID, lldp_portID,") -> (",datapath.id,in_port,")"
            return
        
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def send_flow_stats_request(self):
        for datapath in self.datapaths.values():
            ofp = datapath.ofproto
            parser = datapath.ofproto_parser
            req=parser.OFPFlowStatsRequest(datapath)
        
            datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply,MAIN_DISPATCHER)
    def flow_stat_reply_handler(self,ev):
        
        total_flows=[]
        for stat in ev.msg.body:
            flows={}
            flows['table_id']=stat.table_id
            flows['duration_sec']=stat.duration_sec
            flows['priority']=stat.priority
            flows['idle_timeout']=stat.idle_timeout
            flows['hard_timeout']=stat.hard_timeout
            flows['flags']=stat.flags
            flows['cookie']=stat.cookie
            flows['packet_count']=stat.packet_count
            flows['byte_count']=stat.byte_count
            flows['match']=str(stat.match)
            flows['instructions']=str(stat.instructions)
        
            total_flows.append(flows)    
        self.flow_table[str(ev.msg.datapath.id)]=total_flows
    
    def send_port_desc_stats_request(self,datapath):
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPPortDescStatsRequest(datapath, 0)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        self.port[str(ev.msg.datapath.id)]={}
        for p in ev.msg.body:
            tmp={}
            tmp["port_no"]=p.port_no
            tmp["hw_addr"]=p.hw_addr
            tmp["name"]=p.name
            tmp["config"]=p.config
            tmp["state"]=p.state
            tmp["curr"]=p.curr
            tmp["advertised"]=p.advertised
            tmp["supported"]=p.supported
            tmp["peer"]=p.peer
            tmp["curr_speed"]=p.curr_speed
            tmp["max_speed"]=p.max_speed
            self.port[str(ev.msg.datapath.id)][str(p.port_no)]=tmp
    
class SimpleSwitchController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(SimpleSwitchController, self).__init__(req, link, data, **config)
        self.simpl_switch_spp = data[simple_switch_instance_name]

    @route('simpleswitch', url+'flowtable/{dpid}', methods=['GET'])
    def get_flow_table(self, req, **kwargs):
        simple_switch=self.simpl_switch_spp
        dpid = kwargs['dpid']

        simple_switch.send_flow_stats_request()
        time.sleep(0.1)
        if dpid in simple_switch.flow_table:
            body = json.dumps(simple_switch.flow_table[dpid])
            return Response(content_type='application/json', body=body)

    @route('simpleswitch', url+'flowtable/{dpid}', methods=['PUT'])
    def set_flow_table(self, req, **kwargs):
        simple_switch=self.simpl_switch_spp
        dpid=kwargs['dpid']
        flow=json.loads(req.body)

        datapath=simple_switch.datapaths[dpid]
        parser = datapath.ofproto_parser
        
        match_dic={}
        if 'eth_type' in flow : match_dic['eth_type']=int(flow['eth_type'],16)
        if 'in_port' in flow : match_dic['in_port']=int(flow['in_port'])
        if 'ipv4_src' in flow : match_dic['ipv4_src']=flow['ipv4_src']
        if 'ipv4_dst' in flow : match_dic['ipv4_dst']=flow['ipv4_dst']
        if 'eth_src' in flow : match_dic['eth_src']=flow['eth_src']
        if 'eth_dst' in flow : match_dic['eth_dst']=flow['eth_dst']
        
        match=parser.OFPMatch(**match_dic)
        actions = []
        if flow['action']=='deny':
            simple_switch.add_flow(datapath, 0, match, actions)
        elif flow['action']=='delete':
            simple_switch.del_flow(datapath,match)

    @route('simpleswitch', url+'switchDPID', methods=['GET'])
    def get_switch_dpid(self, req, **kwargs):
        simple_switch=self.simpl_switch_spp
        body = json.dumps(simple_switch.switch)
        return Response(content_type='application/json', body=body)
   
    @route('simpleswitch', url+'switch/{dpid}', methods=['GET'])
    def get_switch_desc(self, req, **kwargs):
        simple_switch=self.simpl_switch_spp
        dpid = kwargs['dpid']
        body=json.dumps(simple_switch.switch[dpid])
        return Response(content_type='application/json', body=body)
    
    @route('simpleswitch', url+'portID', methods=['GET'])
    def get_port_id(self, req, **kwargs):
        simple_switch=self.simpl_switch_spp
        body = json.dumps(simple_switch.port)
        return Response(content_type='application/json', body=body)
    
    @route('simpleswitch', url+'port/{dpid}/{port}', methods=['GET'])
    def get_port_desc(self, req, **kwargs):
        simple_switch=self.simpl_switch_spp
        dpid = kwargs['dpid']
        port = kwargs['port']
        
        simple_switch.send_port_desc_stats_request(simple_switch.datapaths[dpid])
        time.sleep(0.1)
        body = json.dumps(simple_switch.port[dpid][port])
        return Response(content_type='application/json', body=body)

    @route('simpleswitch', url+'link', methods=['GET'])
    def get_link(self, req, **kwargs):
        simple_switch = self.simpl_switch_spp
        simple_switch.link = {}
        simple_switch.link_discovery()
        time.sleep(0.1)
        body = json.dumps(simple_switch.link)
        return Response(content_type='application/json', body=body)
