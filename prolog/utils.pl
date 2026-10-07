endpointServices(Endpoint, Services) :-
    endpoint(Endpoint, Interactions),
    findall(Service,
        (member(Interaction,Interactions), interactionService(Interaction,Service)),
        RepeatedServices),
    sort(RepeatedServices, Services).

interactionService((A,_,_), A).
interactionService((_,B,_), B).
