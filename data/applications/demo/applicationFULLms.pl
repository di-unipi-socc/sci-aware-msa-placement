application(demo6, [ms1, ms2, ms3, ms4, ms5, ms6], [ep1, ep2, ep3, ep4, ep5, ep6]).

microservice(ms1, rr(0.1, 0.1, 0.1, 0.1), 1).
microservice(ms2, rr(0.1, 0.1, 0.1, 0.1), 1).
microservice(ms3, rr(0.1, 0.1, 0.1, 0.1), 1).
microservice(ms4, rr(0.1, 0.1, 0.1, 0.1), 1).
microservice(ms5, rr(0.1, 0.1, 0.1, 0.1), 1).
microservice(ms6, rr(0.1, 0.1, 0.1, 0.1), 1).

% Assumed sequential calls; synthetic AvgGB per consecutive pair/invocation.
endpoint(ep1, [ms1], 0.000001).
endpoint(ep2, [ms1, ms2], 0.000001).
endpoint(ep3, [ms1, ms2, ms3], 0.000001).
endpoint(ep4, [ms1, ms2, ms3, ms4], 0.000001).
endpoint(ep5, [ms1, ms2, ms3, ms4, ms5], 0.000001).
endpoint(ep6, [ms1, ms2, ms3, ms4, ms5, ms6], 0.000001).

probability(ep1, 0.166).
probability(ep2, 0.166).
probability(ep3, 0.166).
probability(ep4, 0.166).
probability(ep5, 0.166).
probability(ep6, 0.17).

functionalUnits(demo6, 10000).
