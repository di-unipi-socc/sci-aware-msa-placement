:- use_module(library(solution_sequences)).

placement(Mode, Scope, App, P, SCI, Nodes) :-
    heuristicPlacement(Mode, Scope, App, P),
    placementSCI(Scope, App, P, SCI),
    involvedNodes(P, Nodes).

heuristicPlacement(capacityonly(K), _, App, P) :-
    servicesByRequirement(App, Services),
    nodesByCapacity(Nodes),
    bestOfFirstKPlacements(K, App, Services, Nodes, P).
heuristicPlacement(greenonly(K), _, App, P) :-
    servicesByRequirement(App, Services),
    nodesByGreenness(Nodes),
    bestOfFirstKPlacements(K, App, Services, Nodes, P).
heuristicPlacement(networkaware(Alpha,Beta,Gamma), _, App, P) :-
    servicesByTraffic(App, Services),
    nodesByCombinedScore(Alpha, Beta, Gamma, Nodes),
    once(eligiblePlacement(Services, Nodes, P)).
heuristicPlacement(scigreedy, Scope, App, P) :-
    greedyPlacement(Scope, App, P).
heuristicPlacement(scilocalsearch, Scope, App, P) :-
    greedyPlacement(Scope, App, InitialP),
    placementSCI(Scope, App, InitialP, InitialSCI),
    improvePlacement(Scope, App, InitialP, InitialSCI, P, _).

servicesByRequirement(App, Services) :-
    application(App, Microservices, _),
    findall(candidate(Score,M),
        (member(M,Microservices), serviceRequirementScore(App,M,Score)),
        Candidates),
    sort(1, @=<, Candidates, Sorted),
    findall(M, member(candidate(_,M), Sorted), Services).

servicesByTraffic(App, Services) :-
    application(App, Microservices, _),
    findall(candidate(Traffic,M),
        (member(M,Microservices), serviceTraffic(App,M,Traffic)),
        Candidates),
    sort(1, @>=, Candidates, Sorted),
    findall(M, member(candidate(_,M), Sorted), Services).

nodesByCapacity(Nodes) :-
    findall(candidate(Score,N), capacityScore(N,Score), Candidates),
    sort(1, @=<, Candidates, Sorted),
    findall(N, member(candidate(_,N), Sorted), Nodes).

nodesByGreenness(Nodes) :-
    findall(candidate(Score,N), greenScore(N,Score), Candidates),
    sort(1, @=<, Candidates, Sorted),
    findall(N, member(candidate(_,N), Sorted), Nodes).

nodesByCombinedScore(Alpha, Beta, Gamma, Nodes) :-
    findall(candidate(Score,N), nodeScore(Alpha,Beta,Gamma,N,Score), Candidates),
    sort(1, @=<, Candidates, Sorted),
    findall(N, member(candidate(_,N), Sorted), Nodes).

bestOfFirstKPlacements(K, App, Services, Nodes, BestP) :-
    findnsols(K, P, eligiblePlacement(Services, Nodes, P), Placements),
    bestTotalSCIPlacement(App, Placements, BestP).

bestTotalSCIPlacement(App, [P|Placements], BestP) :-
    placementSCI(components_and_network, App, P, SCI),
    bestTotalSCIPlacement(App, Placements, p(SCI,P), p(_,BestP)).

bestTotalSCIPlacement(App, [P|Placements], p(BestSCI,_), Best) :-
    placementSCI(components_and_network, App, P, SCI),
    SCI < BestSCI,
    bestTotalSCIPlacement(App, Placements, p(SCI,P), Best).
bestTotalSCIPlacement(App, [P|Placements], p(BestSCI,BestP), Best) :-
    placementSCI(components_and_network, App, P, SCI),
    SCI >= BestSCI,
    bestTotalSCIPlacement(App, Placements, p(BestSCI,BestP), Best).
bestTotalSCIPlacement(_, [], Best, Best).

greedyPlacement(Scope, App, P) :-
    servicesByTraffic(App, Services),
    greedyPlacement(Services, Scope, App, [], P).

greedyPlacement([M|Ms], Scope, App, P, NewP) :-
    microservice(M, RR, _),
    findall(candidate(Cost,Tie,N),
        (placementNode(N,P,RR),
         greedyCost(Scope,App,[on(M,N)|P],Cost,Tie)),
        Candidates),
    sort(Candidates, [candidate(_,_,BestN)|_]),
    greedyPlacement(Ms, Scope, App, [on(M,BestN)|P], NewP).
greedyPlacement([], _, _, P, P).

greedyCost(components_only, App, P, SCI, 0) :-
    componentPlacementSCI(App, P, SCI).
greedyCost(components_and_network, App, P, SCI, NetworkSCI) :-
    componentPlacementSCI(App, P, ComponentSCI),
    partialNetworkSCI(App, P, NetworkSCI),
    SCI is ComponentSCI + NetworkSCI.

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
    application(App, _, Endpoints),
    functionalUnits(App, FunctionalUnits),
    sci(Endpoints, FunctionalUnits, P, SCI).

placementSCI(components_only, App, P, SCI) :-
    componentPlacementSCI(App, P, SCI).
placementSCI(components_and_network, App, P, SCI) :-
    componentPlacementSCI(App, P, ComponentSCI),
    networkSCI(App, P, NetworkSCI),
    SCI is ComponentSCI + NetworkSCI.
