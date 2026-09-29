% Endpoint volumes: GB per consecutive pair and invocation.
% Montpellier profiles: operational/production kgCO2eq/GB (Ficher, Table III).
% Linear distance scaling assumes a 700 km Orsay-Montpellier reference.

networkSCI(App, P, SCI) :- networkSCI(App, P, O, M), SCI is O + M.
networkSCI(App, P, O, M) :-
    application(App, _, EPs),
    networkEndpointsSCI(EPs, P, O, M).

networkEndpointsSCI([EP|EPs], P, O, M) :-
    endpointNetworkSCI(EP, P, CurrentO, CurrentM),
    networkEndpointsSCI(EPs, P, RestO, RestM),
    O is CurrentO + RestO, M is CurrentM + RestM.
networkEndpointsSCI([], _, 0, 0).

endpointNetworkSCI(EP, P, O, M) :-
    endpoint(EP, Services, AvgGB),
    probability(EP, Prob),
    placementNodes(Services, P, Nodes),
    chainSCI(Nodes, AvgGB, ChainO, ChainM),
    O is Prob * ChainO, M is Prob * ChainM.

chainSCI([N1,N2|Nodes], AvgGB, O, M) :-
    transferCarbon(N1, N2, AvgGB, CurrentO, CurrentM),
    chainSCI([N2|Nodes], AvgGB, RestO, RestM),
    O is CurrentO + RestO, M is CurrentM + RestM.
chainSCI([_], _, 0, 0).
chainSCI([], _, 0, 0).

transferCarbon(_, _, 0, 0, 0).
transferCarbon(N1, N2, GB, O, M) :-
    GB > 0,
    networkIntensity(N1, N2, OPerGB, MPerGB),
    O is GB * OPerGB, M is GB * MPerGB.

networkIntensity(N, N, 0, 0).
networkIntensity(N1, N2, O, M) :-
    dif(N1, N2),
    route(N1, N2, DistKM, Profile),
    routeProfile(Profile, ORef, MRef),
    O is ORef * DistKM / 700, % 700 km Orsay-Montpellier reference. Can become a parameter if needed.
    M is MRef * DistKM / 700.

