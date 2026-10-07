:- table operationalFactors/1.
:- table manufacturingFactors/1.
:- table capacityValues/4.
:- table serviceRequirementValues/5.
:- table serviceTrafficValues/3.
:- table outgoingNetworkIntensities/2.
:- table networkIntensities/1.

operationalFactor(N, Factor) :-
    node(N, _, PowerPerCPU, _, _, PUE),
    carbon_intensity(N, CarbonIntensity),
    Factor is PUE * CarbonIntensity * PowerPerCPU.

manufacturingFactor(N, Factor) :-
    node(N, _, _, ExpectedLifetime, TotalEmbodiedEmissions, _),
    Factor is TotalEmbodiedEmissions / ExpectedLifetime.

greenScore(N, Score) :-
    operationalFactor(N, OperationalFactor),
    operationalFactors(OperationalFactors),
    normalizedLowerScore(OperationalFactor, OperationalFactors, OperationalScore),
    manufacturingFactor(N, ManufacturingFactor),
    manufacturingFactors(ManufacturingFactors),
    normalizedLowerScore(ManufacturingFactor, ManufacturingFactors, ManufacturingScore),
    Score is 0.5 * OperationalScore + 0.5 * ManufacturingScore.

operationalFactors(Factors) :- findall(Factor, operationalFactor(_, Factor), Factors).
manufacturingFactors(Factors) :- findall(Factor, manufacturingFactor(_, Factor), Factors).

capacityScore(N, Score) :-
    node(N, tor(CPU,RAM,BWIn,BWOut), _, _, _, _),
    capacityValues(CPUValues, RAMValues, BWInValues, BWOutValues),
    normalizedHigherScore(CPU, CPUValues, CPUScore),
    normalizedHigherScore(RAM, RAMValues, RAMScore),
    normalizedHigherScore(BWIn, BWInValues, BWInScore),
    normalizedHigherScore(BWOut, BWOutValues, BWOutScore),
    Score is 0.25 * CPUScore + 0.25 * RAMScore + 0.25 * BWInScore + 0.25 * BWOutScore.

capacityValues(CPUValues, RAMValues, BWInValues, BWOutValues) :-
    findall(Value, node(_,tor(Value,_,_,_),_,_,_,_), CPUValues),
    findall(Value, node(_,tor(_,Value,_,_),_,_,_,_), RAMValues),
    findall(Value, node(_,tor(_,_,Value,_),_,_,_,_), BWInValues),
    findall(Value, node(_,tor(_,_,_,Value),_,_,_,_), BWOutValues).

serviceRequirementScore(App, M, Score) :-
    microservice(M, rr(CPU,RAM,BWIn,BWOut), _),
    serviceRequirementValues(App, CPUValues, RAMValues, BWInValues, BWOutValues),
    normalizedHigherScore(CPU, CPUValues, CPUScore),
    normalizedHigherScore(RAM, RAMValues, RAMScore),
    normalizedHigherScore(BWIn, BWInValues, BWInScore),
    normalizedHigherScore(BWOut, BWOutValues, BWOutScore),
    Score is 0.25 * CPUScore + 0.25 * RAMScore + 0.25 * BWInScore + 0.25 * BWOutScore.

serviceRequirementValues(App, CPUValues, RAMValues, BWInValues, BWOutValues) :-
    application(App, Microservices, _),
    findall(Value, (member(Service,Microservices), microservice(Service,rr(Value,_,_,_),_)), CPUValues),
    findall(Value, (member(Service,Microservices), microservice(Service,rr(_,Value,_,_),_)), RAMValues),
    findall(Value, (member(Service,Microservices), microservice(Service,rr(_,_,Value,_),_)), BWInValues),
    findall(Value, (member(Service,Microservices), microservice(Service,rr(_,_,_,Value),_)), BWOutValues).

serviceTraffic(App, M, Traffic) :- serviceTrafficValues(App, M, TrafficValues), sum_list(TrafficValues, Traffic).

serviceTrafficValues(App, M, TrafficValues) :-
    application(App, _, Endpoints),
    findall(WeightedGB,
        (member(Endpoint, Endpoints),
         endpoint(Endpoint, Interactions),
         probability(Endpoint, Probability),
         member((A,B,AvgGB), Interactions),
         incidentService(M, A, B),
         WeightedGB is Probability * AvgGB),
        TrafficValues).

incidentService(M, M, _).
incidentService(M, _, M).

centralityScore(N, Score) :-
    outgoingNetworkIntensity(N, Intensity),
    networkIntensities(Intensities),
    normalizedLowerScore(Intensity, Intensities, Score).

outgoingNetworkIntensity(N, Intensity) :-
    outgoingNetworkIntensities(N, RouteIntensities),
    average(RouteIntensities, Intensity).

outgoingNetworkIntensities(N, RouteIntensities) :-
    node(N, _, _, _, _, _),
    findall(RouteIntensity,
        (node(Other,_,_,_,_,_),
         dif(N, Other),
         networkIntensity(N, Other, OperationalPerGB, EmbodiedPerGB),
         RouteIntensity is OperationalPerGB + EmbodiedPerGB),
        RouteIntensities).

networkIntensities(Intensities) :- findall(Value, outgoingNetworkIntensity(_, Value), Intensities).

nodeScore(Alpha, Beta, Gamma, N, Score) :-
    greenScore(N, GreenScore),
    capacityScore(N, CapacityScore),
    centralityScore(N, CentralityScore),
    Score is Alpha * GreenScore + Beta * CapacityScore + Gamma * CentralityScore.

normalizedLowerScore(Value, Values, Score) :-
    min_list(Values, Min), max_list(Values, Max),
    normalizedLowerScore(Value, Min, Max, Score).

normalizedLowerScore(_, M, M, 0).
normalizedLowerScore(Value, Min, Max, Score) :-
    Min =\= Max,
    Score is (Value - Min) / (Max - Min).

normalizedHigherScore(Value, Values, Score) :-
    min_list(Values, Min), max_list(Values, Max),
    normalizedHigherScore(Value, Min, Max, Score).

normalizedHigherScore(_, M, M, 0).
normalizedHigherScore(Value, Min, Max, Score) :-
    Min =\= Max,
    Score is (Max - Value) / (Max - Min).

average(Values, Average) :-
    sum_list(Values, Sum),
    length(Values, Count),
    Average is Sum / Count.
