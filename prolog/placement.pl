:- ['utils.pl', 'network.pl', 'score.pl', 'heuristics.pl'].

:- set_prolog_flag(stack_limit, 128 000 000 000).
:- set_prolog_flag(last_call_optimisation, true).
:- set_prolog_flag(answer_write_options,[max_depth(0), spacing(next_argument)]).

timedPlacement(Mode, Scope, App, P, SCI, N, Time) :-
    statistics(cputime, TStart),
    placement(Mode, Scope, App, P, SCI, N),
    statistics(cputime, TEnd),
    Time is TEnd - TStart.

eligiblePlacement(LstMs, LstN, P) :- eligiblePlacement(LstMs, LstN, [], P).
eligiblePlacement(LstMs, P) :- eligible(LstMs, [], P).
eligiblePlacement([M|LstMs], LstN, P, NewP) :-
    microservice(M, RR, _),
    member(N,LstN), placementNode(N, P, RR),
    eligiblePlacement(LstMs, LstN, [on(M,N)|P], NewP).
eligiblePlacement([], _, P, P).

eligible([Ms|LstMs], P, NewP) :-
    microservice(Ms, RR, _),
    placementNode(N, P, RR),
    eligible(LstMs, [on(Ms,N)|P], NewP).
eligible([], P, P).

placementNode(N, P, rr(CPUReq, RAMReq, BWinReq, BWoutReq)) :-
    node(N, tor(CPU, RAM, BWin, BWout), _, _, _, _),
    hardwareUsedAtNode(N, P, rr(UCPU, URAM, UBWin, UBWout)),
    CPU >= UCPU + CPUReq,
    RAM >= URAM + RAMReq,
    BWin >= UBWin + BWinReq,
    BWout >= UBWout + BWoutReq.

involvedNodes(P, InvolvedNodes) :-
    findall(N, distinct(node(N,_), member(on(_,N),P)), Nodes),
    length(Nodes, InvolvedNodes).

hardwareUsedAtNode(N, P, rr(UCPU, URAM, UBWin, UBWout)) :-
    findall(rr(CPU,RAM,BWin,BWout),
        (member(on(Ms,N),P), microservice(Ms,rr(CPU,RAM,BWin,BWout),_)),
        RRs),
    sumHWReqs(RRs, rr(UCPU, URAM, UBWin, UBWout)).

sumHWReqs([rr(CPU,RAM,BWin,BWout)|RRs], rr(TCPU,TRAM,TBWin,TBWout)) :-
    sumHWReqs(RRs, rr(AccCPU,AccRAM,AccBWin,AccBWout)),
    TCPU is AccCPU + CPU,
    TRAM is AccRAM + RAM,
    TBWin is AccBWin + BWin,
    TBWout is AccBWout + BWout.
sumHWReqs([], rr(0,0,0,0)).

sci(EPs, R, P, SCI) :-
    sci(EPs, R, P, Operational, Embodied),
    SCI is Operational + Embodied.
sci([EP|EPs], R, P, Operational, Embodied) :-
    endpointSCI(EP, R, P, CurrentOperational, CurrentEmbodied),
    sci(EPs, R, P, RestOperational, RestEmbodied),
    Operational is CurrentOperational + RestOperational,
    Embodied is CurrentEmbodied + RestEmbodied.
sci([], _, _, 0, 0).

endpointSCI(EP, R, P, SCI) :-
    endpointSCI(EP, R, P, Operational, Embodied),
    SCI is Operational + Embodied.
endpointSCI(EP, R, P, Operational, Embodied) :-
    endpointServices(EP, Sequence),
    sort(Sequence, EPMs),
    findall(on(Ms,N), (member(Ms,EPMs), member(on(Ms,N),P)), FilteredP),
    probability(EP, Prob),
    carbonEmissions(FilteredP, OperationalCarbon, EmbodiedCarbon),
    Operational is (OperationalCarbon / R) * Prob,
    Embodied is (EmbodiedCarbon / R) * Prob.

carbonEmissions(P, C) :-
    carbonEmissions(P, Operational, Embodied),
    C is Operational + Embodied.

carbonEmissions([on(Ms,N)|P], Operational, Embodied) :-
    carbonEmissions(P, RestOperational, RestEmbodied),
    operationalCarbon(N, Ms, O),
    embodiedCarbon(N, Ms, E),
    Operational is RestOperational + O,
    Embodied is RestEmbodied + E.
carbonEmissions([], 0, 0).

operationalEnergy(N, Ms, E) :-
    node(N, _, PowerPerCPU, _, _, PUE),
    microservice(Ms, rr(CPUReq,_,_,_), TiR),
    E is PUE * (TiR * 365 * 24) * PowerPerCPU * CPUReq.

operationalCarbon(N, Ms, O) :-
    carbon_intensity(N, I),
    operationalEnergy(N, Ms, E),
    O is E * I.

embodiedCarbon(N, Ms, M) :-
    node(N, tor(CPU,_,_,_), _, EL, TE, _),
    microservice(Ms, rr(CPUReq,_,_,_), TiR),
    TS is TiR / EL,
    RS is CPUReq / CPU,
    M is TE * TS * RS.
