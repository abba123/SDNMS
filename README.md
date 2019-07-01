# SDNMS
SDNMS is a networking monitor system for SDN(Software Defined Netowrk). 
We provide a centralized control for all SDN switch.

# Related Installation
* *Ryu:* [https://osrg.github.io/ryu/](https://osrg.github.io/ryu/)
* *OpnevSwitch:* [https://www.openvswitch.org/](https://www.openvswitch.org/)
* *Mininet:* [http://mininet.org/](http://mininet.org/)

# Start
We use mininet to create virtual network

    mn --topo single,3 --mac --switch ovsk --controller=remote

Start our Ryu controller

    ryu-manager --verbose mySwitch.py
    
Open CLI

    python ControllerCLI.py
    
# What we can do

Details in the [user guide](https://github.com/abba123/SDNMS/blob/master/guide.md)
      
# TODO

- [ ] Port statistic
- [ ] host information
- [ ] delay between switch

# Help
connect me a0981861951@gmail.com
