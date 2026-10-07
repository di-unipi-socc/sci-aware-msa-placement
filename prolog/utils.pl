:-set_prolog_flag(stack_limit, 16 000 000 000).
:-set_prolog_flag(last_call_optimisation, true).

:- dynamic endpoint/2, endpoint/3.

endpointServices(EP, Services) :- endpoint(EP, Services, _).
endpointServices(EP, Services) :- endpoint(EP, Services).

placementNodes([S|Services], P, [N|Nodes]) :-
    member(on(S,N), P),
    placementNodes(Services, P, Nodes).
placementNodes([], _, []).
