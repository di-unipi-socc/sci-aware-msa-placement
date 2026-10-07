:- dynamic of/2, mf/2.
:- dynamic maxOF/1, minOF/1.
:- dynamic maxMF/1, minMF/1.
:- dynamic maxResources/4, minResources/4.

placement(Mode, Scope, App, P, SCI, Nodes) :-
    heuristicPlacement(Mode, Scope, App, P),
    placementSCI(Scope, App, P, SCI),
    involvedNodes(P, Nodes).

heuristicPlacement(greenonly, Scope, App, P) :- heuristicPlacement(linearcombination(1), Scope, App, P).
heuristicPlacement(capacityonly, Scope, App, P) :- heuristicPlacement(linearcombination(0), Scope, App, P).
heuristicPlacement(linearcombination, Scope, App, P) :- heuristicPlacement(linearcombination(0.5), Scope, App, P).
heuristicPlacement(linearcombination(CarbonWeight), _, App, P) :-
    scoredNodes(linearcombination(CarbonWeight), Nodes),
    scoredMicroservices(Microservices),
    application(App, _, _),
    eligiblePlacement(Microservices, Nodes, P).
heuristicPlacement(base, _, App, P) :-
    application(App, Ms, _),
    eligiblePlacement(Ms, P).
heuristicPlacement(evaluatePlacement, _, _, _).
heuristicPlacement(exhaustive, Scope, App, BestP) :-
    findall(p(SCI,P),
        (heuristicPlacement(base,Scope,App,P), placementSCI(Scope,App,P,SCI)),
        [First|Rest]),
    findMinPlacement(Rest, First, p(_,BestP)).
heuristicPlacement(networkonly, _, App, P) :- greedyPlacement(networkonly, App, P).
heuristicPlacement(scigreedy, Scope, App, P) :- greedyPlacement(scigreedy(Scope), App, P).
heuristicPlacement(scilocalsearch, Scope, App, P) :-
    greedyPlacement(scigreedy(Scope), App, InitialP),
    placementSCI(Scope, App, InitialP, InitialSCI),
    improvePlacement(Scope, App, InitialP, InitialSCI, P, _).

greedyPlacement(Mode, App, P) :-
    trafficOrderedServices(App, Services),
    greedyPlacement(Services, Mode, App, [], P).
greedyPlacement([M|Ms], Mode, App, P, NewP) :-
    microservice(M, RR, _),
    findall(candidate(Cost,Tie,N),
        (placementNode(N, P, RR), greedyCost(Mode, App, [on(M,N)|P], Cost, Tie)),
        Candidates),
    sort(Candidates, [candidate(_,_,BestN)|_]),
    greedyPlacement(Ms, Mode, App, [on(M,BestN)|P], NewP).
greedyPlacement([], _, _, P, P).

greedyCost(networkonly, App, P, NetworkSCI, ComponentSCI) :-
    partialNetworkSCI(App, P, NetworkSCI),
    componentPlacementSCI(App, P, ComponentSCI).
greedyCost(scigreedy(components_only), App, P, SCI, 0) :- componentPlacementSCI(App, P, SCI).
greedyCost(scigreedy(components_and_network), App, P, SCI, NetworkSCI) :-
    componentPlacementSCI(App, P, ComponentSCI),
    partialNetworkSCI(App, P, NetworkSCI),
    SCI is ComponentSCI + NetworkSCI.

trafficOrderedServices(App, Services) :-
    application(App, Ms, _),
    findall(traffic(Traffic,M), (member(M,Ms), serviceTraffic(App,M,Traffic)), Ranked),
    sort(1, @>=, Ranked, Sorted),
    findall(M, member(traffic(_,M), Sorted), Services).

serviceTraffic(App, M, Traffic) :-
    application(App, _, EPs),
    findall(WeightedGB,
        (member(EP,EPs), endpoint(EP,Sequence,AvgGB), probability(EP,Prob),
         endpointPair(Sequence,A,B), incidentService(M,A,B), WeightedGB is Prob * AvgGB),
        TrafficValues),
    sum_list(TrafficValues, Traffic).

endpointPair([A,B|_], A, B).
endpointPair([_|Services], A, B) :- endpointPair(Services, A, B).

incidentService(M, M, _).
incidentService(M, _, M).

partialNetworkSCI(App, P, SCI) :-
    application(App, _, EPs),
    partialNetworkSCI(EPs, P, SCI).
partialNetworkSCI([EP|EPs], P, SCI) :-
    endpoint(EP, Services, AvgGB),
    probability(EP, Prob),
    partialChainSCI(Services, P, AvgGB, ChainSCI),
    partialNetworkSCI(EPs, P, RestSCI),
    SCI is Prob * ChainSCI + RestSCI.
partialNetworkSCI([], _, 0).

partialChainSCI([A,B|Services], P, AvgGB, SCI) :-
    partialTransferSCI(A, B, P, AvgGB, CurrentSCI),
    partialChainSCI([B|Services], P, AvgGB, RestSCI),
    SCI is CurrentSCI + RestSCI.
partialChainSCI([_], _, _, 0).
partialChainSCI([], _, _, 0).

partialTransferSCI(A, B, P, AvgGB, SCI) :-
    findall(Carbon,
        (member(on(A,N1),P), member(on(B,N2),P),
         transferCarbon(N1,N2,AvgGB,O,M), Carbon is O + M),
        Values),
    sum_list(Values, SCI).

improvePlacement(Scope, App, P, SCI, BestP, BestSCI) :-
    bestMove(Scope, App, P, NewP, NewSCI),
    NewSCI < SCI,
    improvePlacement(Scope, App, NewP, NewSCI, BestP, BestSCI).
improvePlacement(Scope, App, P, SCI, P, SCI) :-
    bestMove(Scope, App, P, _, NewSCI),
    NewSCI >= SCI.
improvePlacement(Scope, App, P, SCI, P, SCI) :-
    \+ bestMove(Scope, App, P, _, _).

bestMove(Scope, App, P, BestP, BestSCI) :-
    findall(move(SCI,NewP),
        (movePlacement(P,NewP), placementSCI(Scope,App,NewP,SCI)),
        Moves),
    sort(Moves, [move(BestSCI,BestP)|_]).

movePlacement(P, [on(M,NewN)|Rest]) :-
    select(on(M,OldN), P, Rest),
    microservice(M, RR, _),
    node(NewN, _, _, _, _, _),
    dif(OldN, NewN),
    placementNode(NewN, Rest, RR).

componentPlacementSCI(App, P, SCI) :-
    application(App, _, EPs),
    functionalUnits(App, R),
    sci(EPs, R, P, SCI).

placementSCI(components_only, App, P, SCI) :-
    componentPlacementSCI(App, P, SCI).
placementSCI(components_and_network, App, P, SCI) :-
    componentPlacementSCI(App, P, ComponentSCI),
    networkSCI(App, P, NetworkSCI),
    SCI is ComponentSCI + NetworkSCI.

findMinPlacement([p(SCI,P)|Placements], p(OldSCI,_), Best) :-
    SCI < OldSCI,
    findMinPlacement(Placements, p(SCI,P), Best).
findMinPlacement([p(SCI,_)|Placements], p(OldSCI,OldP), Best) :-
    SCI >= OldSCI,
    findMinPlacement(Placements, p(OldSCI,OldP), Best).
findMinPlacement([], P, P).

scoredNodes(linearcombination(CarbonWeight), Nodes) :-
    retractall(cs(_,_)), retractall(rs(_,_)),
    carbonRankingFactors(), resourceRankingFactors(node),
    findall(candidate(CS,RS,N), nodeRankingScore(N,CS,RS), Candidates),
    rankNodesByLinearCombination(CarbonWeight, Candidates, Nodes),
    cleanUp().

nodeRankingScore(N, CS, RS) :-
    carbonScore(N,CS),
    resourceScore(node,N,RS).

rankNodesByLinearCombination(CarbonWeight, Candidates, Nodes) :-
    ResourceWeight is 1 - CarbonWeight,
    findall(candidate(Score,N),
        (member(candidate(CS,RS,N),Candidates),
         Score is CarbonWeight * CS + ResourceWeight * RS),
        Weighted),
    sort(1, @=<, Weighted, Sorted),
    findall(N, member(candidate(_,N),Sorted), Nodes).

scoredMicroservices(Microservices) :-
    retractall(rs(_,_)), resourceRankingFactors(microservice),
    findall(ms(RS,M), resourceScore(microservice,M,RS), Ranked),
    sort(Ranked, Sorted),
    findall(M, member(ms(_,M), Sorted), Microservices),
    cleanUp().

resourceScore(E, CPU, RAM, BWIn, BWOut, RS) :-
    maxResources(MaxCPU,MaxRAM,MaxBWIn,MaxBWOut),
    minResources(MinCPU,MinRAM,MinBWIn,MinBWOut),
    safeROp(0.25, CPU, MaxCPU, MinCPU, P1),
    safeROp(0.25, RAM, MaxRAM, MinRAM, P2),
    safeROp(0.25, BWIn, MaxBWIn, MinBWIn, P3),
    safeROp(0.25, BWOut, MaxBWOut, MinBWOut, P4),
    RS is P1 + P2 + P3 + P4,
    assert(rs(E,RS)).

carbonScore(N, CS) :-
    node(N,_,_,_,_,_),
    of(N,OF), minOF(MinOF), maxOF(MaxOF),
    safeCOp(0.5, OF, MaxOF, MinOF, P1),
    mf(N,MF), minMF(MinMF), maxMF(MaxMF),
    safeCOp(0.5, MF, MaxMF, MinMF, P2),
    CS is P1 + P2,
    assert(cs(N,CS)).

carbonRankingFactors() :-
    findall(OF, nodeOF(N,OF), OFs), max_list(OFs,MaxOF), min_list(OFs,MinOF),
    assert(maxOF(MaxOF)), assert(minOF(MinOF)),
    findall(MF, nodeMF(N,MF), MFs), max_list(MFs,MaxMF), min_list(MFs,MinMF),
    assert(maxMF(MaxMF)), assert(minMF(MinMF)).

nodeOF(N, OF) :-
    node(N,_,PowerPerCPU,_,_,PUE), carbon_intensity(N,I),
    OF is PUE * I * PowerPerCPU,
    assert(of(N,OF)).
nodeMF(N, MF) :-
    node(N,_,_,EL,TE,_),
    MF is TE / EL,
    assert(mf(N,MF)).

resourceScore(microservice, M, RS) :-
    microservice(M,rr(CPU,RAM,BWIn,BWOut),_),
    resourceScore(M,CPU,RAM,BWIn,BWOut,RS).
resourceScore(node, N, RS) :-
    node(N,tor(CPU,RAM,BWIn,BWOut),_,_,_,_),
    resourceScore(N,CPU,RAM,BWIn,BWOut,RS).

resourceRankingFactors(microservice) :-
    findall(CPU,microservice(_,rr(CPU,_,_,_),_),CPUs),
    findall(RAM,microservice(_,rr(_,RAM,_,_),_),RAMs),
    findall(BWIn,microservice(_,rr(_,_,BWIn,_),_),BWIns),
    findall(BWOut,microservice(_,rr(_,_,_,BWOut),_),BWOuts),
    resourceLimits(CPUs,RAMs,BWIns,BWOuts).
resourceRankingFactors(node) :-
    findall(CPU,node(_,tor(CPU,_,_,_),_,_,_,_),CPUs),
    findall(RAM,node(_,tor(_,RAM,_,_),_,_,_,_),RAMs),
    findall(BWIn,node(_,tor(_,_,BWIn,_),_,_,_,_),BWIns),
    findall(BWOut,node(_,tor(_,_,_,BWOut),_,_,_,_),BWOuts),
    resourceLimits(CPUs,RAMs,BWIns,BWOuts).

resourceLimits(CPUs, RAMs, BWIns, BWOuts) :-
    max_list(CPUs,MaxCPU), min_list(CPUs,MinCPU),
    max_list(RAMs,MaxRAM), min_list(RAMs,MinRAM),
    max_list(BWIns,MaxBWIn), min_list(BWIns,MinBWIn),
    max_list(BWOuts,MaxBWOut), min_list(BWOuts,MinBWOut),
    assert(maxResources(MaxCPU,MaxRAM,MaxBWIn,MaxBWOut)),
    assert(minResources(MinCPU,MinRAM,MinBWIn,MinBWOut)).

cleanUp() :-
    retractall(of(_,_)), retractall(maxOF(_)), retractall(minOF(_)),
    retractall(mf(_,_)), retractall(maxMF(_)), retractall(minMF(_)),
    retractall(maxResources(_,_,_,_)), retractall(minResources(_,_,_,_)).

safeCOp(F, E, MaxE, MinE, R) :-
    O is F * (E - MinE), D is MaxE - MinE,
    safeDiv(O, D, R).
safeROp(F, E, MaxE, MinE, R) :-
    O is F * (MaxE - E), D is MaxE - MinE,
    safeDiv(O, D, R).
safeDiv(_, 0, 0).
safeDiv(_, 0.0, 0).
safeDiv(O, D, R) :- dif(D,0), dif(D,0.0), R is O / D.
