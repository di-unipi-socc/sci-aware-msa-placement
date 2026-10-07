operationalFactor(N, Factor) :-
    node(N, _, PowerPerCPU, _, _, PUE),
    carbon_intensity(N, CarbonIntensity),
    Factor is PUE * CarbonIntensity * PowerPerCPU.

manufacturingFactor(N, Factor) :-
    node(N, _, _, ExpectedLifetime, TotalEmbodiedEmissions, _),
    Factor is TotalEmbodiedEmissions / ExpectedLifetime.

greenScore(N, Score) :-
    operationalFactor(N, OperationalFactor),
    findall(Factor, operationalFactor(_, Factor), OperationalFactors),
    normalizedLowerScore(OperationalFactor, OperationalFactors, OperationalScore),
    manufacturingFactor(N, ManufacturingFactor),
    findall(Factor, manufacturingFactor(_, Factor), ManufacturingFactors),
    normalizedLowerScore(ManufacturingFactor, ManufacturingFactors, ManufacturingScore),
    Score is 0.5 * OperationalScore + 0.5 * ManufacturingScore.

capacityScore(N, Score) :-
    node(N, tor(CPU,RAM,BWIn,BWOut), _, _, _, _),
    findall(Value, node(_,tor(Value,_,_,_),_,_,_,_), CPUValues),
    findall(Value, node(_,tor(_,Value,_,_),_,_,_,_), RAMValues),
    findall(Value, node(_,tor(_,_,Value,_),_,_,_,_), BWInValues),
    findall(Value, node(_,tor(_,_,_,Value),_,_,_,_), BWOutValues),
    normalizedHigherScore(CPU, CPUValues, CPUScore),
    normalizedHigherScore(RAM, RAMValues, RAMScore),
    normalizedHigherScore(BWIn, BWInValues, BWInScore),
    normalizedHigherScore(BWOut, BWOutValues, BWOutScore),
    Score is 0.25 * CPUScore + 0.25 * RAMScore + 0.25 * BWInScore + 0.25 * BWOutScore.

serviceRequirementScore(App, M, Score) :-
    application(App, Microservices, _),
    microservice(M, rr(CPU,RAM,BWIn,BWOut), _),
    findall(Value, (member(Service,Microservices),microservice(Service,rr(Value,_,_,_),_)), CPUValues),
    findall(Value, (member(Service,Microservices),microservice(Service,rr(_,Value,_,_),_)), RAMValues),
    findall(Value, (member(Service,Microservices),microservice(Service,rr(_,_,Value,_),_)), BWInValues),
    findall(Value, (member(Service,Microservices),microservice(Service,rr(_,_,_,Value),_)), BWOutValues),
    normalizedHigherScore(CPU, CPUValues, CPUScore),
    normalizedHigherScore(RAM, RAMValues, RAMScore),
    normalizedHigherScore(BWIn, BWInValues, BWInScore),
    normalizedHigherScore(BWOut, BWOutValues, BWOutScore),
    Score is 0.25 * CPUScore + 0.25 * RAMScore + 0.25 * BWInScore + 0.25 * BWOutScore.

serviceTraffic(App, M, Traffic) :-
    application(App, _, Endpoints),
    findall(WeightedGB,
        (member(Endpoint, Endpoints),
         endpoint(Endpoint, Interactions),
         probability(Endpoint, Probability),
         member((A,B,AvgGB), Interactions),
         incidentService(M, A, B),
         WeightedGB is Probability * AvgGB),
        TrafficValues),
    sum_list(TrafficValues, Traffic).

incidentService(M, M, _).
incidentService(M, _, M).

centralityScore(N, Score) :-
    outgoingNetworkIntensity(N, Intensity),
    findall(Value, outgoingNetworkIntensity(_, Value), Intensities),
    normalizedLowerScore(Intensity, Intensities, Score).

outgoingNetworkIntensity(N, Intensity) :-
    node(N, _, _, _, _, _),
    findall(RouteIntensity,
        (node(Other,_,_,_,_,_),
         dif(N, Other),
         networkIntensity(N, Other, OperationalPerGB, EmbodiedPerGB),
         RouteIntensity is OperationalPerGB + EmbodiedPerGB),
        RouteIntensities),
    average(RouteIntensities, Intensity).

nodeScore(Alpha, Beta, Gamma, N, Score) :-
    greenScore(N, GreenScore),
    capacityScore(N, CapacityScore),
    centralityScore(N, CentralityScore),
    Score is Alpha * GreenScore + Beta * CapacityScore + Gamma * CentralityScore.

normalizedLowerScore(Value, Values, Score) :-
    min_list(Values, Min),
    max_list(Values, Max),
    normalizedLowerScore(Value, Min, Max, Score).

normalizedLowerScore(_, Min, Max, 0) :- Min =:= Max.
normalizedLowerScore(Value, Min, Max, Score) :-
    Min =\= Max,
    Score is (Value - Min) / (Max - Min).

normalizedHigherScore(Value, Values, Score) :-
    min_list(Values, Min),
    max_list(Values, Max),
    normalizedHigherScore(Value, Min, Max, Score).

normalizedHigherScore(_, Min, Max, 0) :- Min =:= Max.
normalizedHigherScore(Value, Min, Max, Score) :-
    Min =\= Max,
    Score is (Max - Value) / (Max - Min).

average(Values, Average) :-
    sum_list(Values, Sum),
    length(Values, Count),
    Average is Sum / Count.
