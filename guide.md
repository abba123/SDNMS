show all command

* help

      >help
      Documented commands (type help <topic>):
      ========================================
      exit  firewall  flows  help  link  port  switch  topo

exit CLI

* exit

      exit

show switch information

* switch [switch]

      >switch s1
      {
          "auxiliary_id": 0, 
          "capabilities": 79, 
          "datapath_id": 1, 
          "n_buffers": 0, 
          "n_tables": 254
      }

show port information

* port [switch] [port]

      >port s1 1
      {
          "advertised": 0, 
          "config": 0, 
          "curr": 2112, 
          "curr_speed": 10000000, 
          "hw_addr": "42:71:7b:b5:1d:60", 
          "max_speed": 0, 
          "name": "s1-eth1", 
          "peer": 0, 
          "port_no": 1, 
          "state": 4, 
          "supported": 0
      }

show flow information

* flows [switch]

      >flows s1
      [
          {
              "byte_count": 630, 
              "cookie": 0, 
              "duration_sec": 156, 
              "flags": 0, 
              "hard_timeout": 0, 
              "idle_timeout": 0, 
              "instructions": "[OFPActionOutput(len=16,max_len=65535,port=4294967293,type=0)]", 
              "match": "OFPMatch(oxm_fields={})", 
              "packet_count": 9, 
              "priority": 0, 
              "table_id": 0
          }
      ]
 

set/delete firewall rule

* firewall [deny/delete] [s1] [in_port=1] [eth_type=0x0800] [src_ip=10.0.0.1] [src_mac=00:00:00:00:00:00] [dst_ip=10.0.0.1] [dst_mac=00:00:00:00:00:00]

      >firewall deny s1 in_port=1 eth_type=0x0800 src_ip=10.0.0.1 src_mac=00:00:00:00:00:00 dst_ip=10.0.0.1 dst_mac=00:00:00:00:00:00 

      >flows s1
      {
        "byte_count": 0,
        "cookie": 0,
        "duration_sec": 5,
        "flags": 0,
        "hard_timeout": 0,
        "idle_timeout": 0,
        "instructions": "[]",
        "match": "OFPMatch(oxm_fields={'eth_dst': '00:00:00:00:00:00', 'ipv4_dst': '10.0.0.1', 'ipv4_src': '10.0.0.1', 'eth_type': 2048, 'eth_src': '00:00:00:00:00:00', 'in_port': 1})",
        "packet_count": 0,
        "priority": 0,
        "table_id": 0
      }  

show link information

* link

      >link
      (s1,2) --- (s3,1)
      (s1,1) --- (s2,1)
      (s3,3) --- (s4,1)
      (s2,2) --- (s3,2)
      
show topology

* topo

      >topo
     ![image](https://github.com/abba123/SDNMS/blob/master/topo.png)
