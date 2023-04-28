
# Configuration Properties

Node Properties

- nodes: NodeSpec
- properties: NodePropertySpec

Interface Properties

- nodes: NodeSpec
- interfaces: InterfaceSpec
- properties: InterfacePropertySpec
- excludeShutInterfaces: bool

BGP Process Configuration

- nodes: NodeSpec
- properties: BgpProcessPropertySpec

BGP Peer Configuration

- nodes: NodeSpec
- properties: BgpPeerPropertySpec

HSRP Properties

- nodes: NodeSpec
- interfaces: InterfaceSpec
- virtualAddresses: IpSpec
- excludeShutInterfaces: bool

OSPF Process Configuration

- nodes: NodeSpec
- properties: OspfProcessPropertySpec

OSPF Interface Configuration

- nodes: NodeSpec
- properties: OspfInterfacePropertySpec

OSPF Area Configuration

- nodes: NodeSpec

Multi-chassis LAG

- nodes: NodeSpec
- mlagIds: MlagIdSpec


IP Owners

- duplicatesOnly: bool

Named Structures

- nodes: NodeSpec
- structureTypes: NamedStructureSpec
- structureNames: str
- ignoreGenerated: bool
- indicatePresence: bool


Defined Structures

- filename: str
- nodes: NodeSpec
- names: str
- types: str


Referenced Structures

- nodes: NodeSpec
- names: str
- types: str

Undefined References

- nodes: NodeSpec

Unused Structures

- nodes: NodeSpec

VLAN Properties

- nodes: NodeSpec
- interfaces: InterfaceSpec
- vlans: str
- excludeShutInterfaces: bool

VRRP Properties

- nodes: NodeSpec
- interfaces: InterfaceSpec
- virtualAddresses: IpSpec
- excludeShutInterfaces: bool

A10 Virtual Server Configuration

- nodes: NodeSpec
- virtualServerIps: IpSpec


F5 BIG-IP VIP Configuration

- nodes: NodeSpec

# Topology

This caterogy of questions is intended to retrieve the network topology used by Batfish. This topology is a combination of information in the snapshot and inference logic (e.g., which interfaces are layer3 neighbors). Currently, Layer 3 topology can be retrieved.

User Provided Layer 1 Topology

- nodes: NodeSpec
- remoteNodes: NodeSpec

Layer 3 Topology

- nodes: NodeSpec
- remoteNodes: NodeSpec

# Routing Protocol Sessions and Policies

This category of questions reveals information regarding which routing protocol sessions are compatibly configured and which ones are established. It also allows to you analyze BGP routing policies.

BGP Session Compatibility

- nodes: NodeSpec
- remoteNodes: NodeSpec
- status: BgpSessionCompatStatusSpec
- type: BgpSessionTypeSpec

BGP Session Status

- nodes: NodeSpec
- remoteNodes: NodeSpec
- status: BgpSessionStatusSpec
- type: BgpSessionTypeSpec

BGP Edges

- nodes: NodeSpec
- remoteNodes: NodeSpec

OSPF Session Compatibility

- nodes: NodeSpec
- remoteNodes: NodeSpec
- statuses: OspfSessionStatusSpec

OSPF Edges

- nodes: NodeSpec
- remoteNodes: NodeSpec

Test Route Policies

- nodes: NodeSpec
- policies: RoutingPolicySpec
- inputRoutes: List of BgpRoute *
- direction: str *


Search Route Policies

- nodes: NodeSpec
- policies: RoutingPolicySpec
- inputConstraints: BgpRouteConstraints
- action: str
- outputConstraints: BgpRouteConstraints
- perPath: bool

# Routing and Forwarding Tables

This category of questions allows you to query the RIBs and FIBs computed by Batfish.

Routes

BGP RIB

EVPN RIB

Longest Prefix Match


# Packet Forwarding

This category of questions allows you to query how different types of traffic is forwarded by the network and if endpoints are able to communicate. You can analyze these aspects in a few different ways.

Traceroute

Bi-directional Traceroute

Reachability

Bi-directional Reachability

Loop detection

Multipath Consistency for host-subnets

Multipath Consistency for router loopbacks

# Access-lists and firewall rules

This category of questions allows you to analyze the behavior of access control lists and firewall rules. It also allows you to comprehensively validate (aka verification) that some traffic is or is not allowed.

Filter Line Reachability

Search Filters

Test Filters

Find Matching Filter Lines

# Snapshot Input

This category of questions allows you to learn how well Batfish understands your network snapshot.

Snapshot Initialization Issues

Snapshot Input File Parse Status

Snapshot Input File Parse Warnings

# IPSec Tunnels

This category of questions allows you to query IPSec sessions and tunnels.

IPSec Session Status

IPSec Edges

# VXLAN and EVPN

This category of questions allows you to query aspects of VXLAN and EVPN configuration and behavior.

VXLAN VNI Properties

VXLAN Edges

L3 EVPN VNIs

# Resolving Specifiers
Specifier grammars allow you to specify complex inputs for Batfish questions. This category of questions reveals how specifier inputs are resolved by Batfish.

Resolve Location Specifier

Resolve Filter Specifier

Resolve Node Specifier

Resolve Interface Specifier

Resolve IPs from Location Specifier

Resolve IP Specifier

# Differential Questions

Differential questions enable you to discover configuration and behavior differences between two snapshot of the network.

Most of the Batfish questions can be run differentially by using snapshot=<current snapshot> and reference_snapshot=<reference snapshot> parameters in .answer(). For example, to view routing table differences between snapshot1 and snapshot0, run bf.q.routes().answer(snapshot="snapshot1", reference_snapshot="snapshot0").

Batfish also has two questions that are exclusively differential.

Compare Filters

Differential Reachability
