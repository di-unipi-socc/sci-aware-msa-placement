% Endpoint volumes are expected GB per interaction and invocation.
% Route profiles are operational/production kgCO2eq/GB at 700 km.

networkSCI(App, P, SCI) :-
    networkSCI(App, P, Operational, Embodied),
    SCI is Operational + Embodied.

networkSCI(App, P, Operational, Embodied) :-
    application(App, _, Endpoints),
    networkEndpointsSCI(Endpoints, P, Operational, Embodied).

networkEndpointsSCI([Endpoint|Endpoints], P, Operational, Embodied) :-
    endpointNetworkSCI(Endpoint, P, CurrentOperational, CurrentEmbodied),
    networkEndpointsSCI(Endpoints, P, RestOperational, RestEmbodied),
    Operational is CurrentOperational + RestOperational,
    Embodied is CurrentEmbodied + RestEmbodied.
networkEndpointsSCI([], _, 0, 0).

endpointNetworkSCI(Endpoint, P, Operational, Embodied) :-
    endpoint(Endpoint, Interactions),
    probability(Endpoint, Probability),
    interactionsSCI(Interactions, P, InteractionOperational, InteractionEmbodied),
    Operational is Probability * InteractionOperational,
    Embodied is Probability * InteractionEmbodied.

interactionsSCI([Interaction|Interactions], P, Operational, Embodied) :-
    interactionSCI(Interaction, P, CurrentOperational, CurrentEmbodied),
    interactionsSCI(Interactions, P, RestOperational, RestEmbodied),
    Operational is CurrentOperational + RestOperational,
    Embodied is CurrentEmbodied + RestEmbodied.
interactionsSCI([], _, 0, 0).

interactionSCI((A,B,AvgGB), P, Operational, Embodied) :-
    member(on(A,N1), P),
    member(on(B,N2), P),
    transferCarbon(N1, N2, AvgGB, Operational, Embodied).

partialNetworkSCI(App, P, SCI) :-
    application(App, _, Endpoints),
    findall(EndpointSCI,
        (member(Endpoint,Endpoints),
         partialEndpointNetworkSCI(Endpoint,P,EndpointSCI)),
        EndpointSCIs),
    sum_list(EndpointSCIs, SCI).

partialEndpointNetworkSCI(Endpoint, P, SCI) :-
    endpoint(Endpoint, Interactions),
    probability(Endpoint, Probability),
    findall(Carbon,
        (member((A,B,AvgGB),Interactions),
         member(on(A,N1),P),
         member(on(B,N2),P),
         transferCarbon(N1,N2,AvgGB,Operational,Embodied),
         Carbon is Operational + Embodied),
        Carbons),
    sum_list(Carbons, InteractionSCI),
    SCI is Probability * InteractionSCI.

transferCarbon(_, _, 0, 0, 0).
transferCarbon(N1, N2, GB, Operational, Embodied) :-
    GB > 0,
    networkIntensity(N1, N2, OperationalPerGB, EmbodiedPerGB),
    Operational is GB * OperationalPerGB,
    Embodied is GB * EmbodiedPerGB.

networkIntensity(N, N, 0, 0).
networkIntensity(N1, N2, Operational, Embodied) :-
    dif(N1, N2),
    route(N1, N2, DistanceKM, Profile),
    routeProfile(Profile, OperationalReference, EmbodiedReference),
    Operational is OperationalReference * DistanceKM / 700,
    Embodied is EmbodiedReference * DistanceKM / 700.
