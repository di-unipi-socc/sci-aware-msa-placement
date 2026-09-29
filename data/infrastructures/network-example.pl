% Synthetic nodes and route assignments. Carbon quantities use kgCO2eq.

node(n1, tor(2,4,1,1), 0.005, 5, 200, 1.1).
node(n2, tor(4,8,2,2), 0.008, 5, 400, 1.2).
node(n3, tor(8,16,10,10), 0.010, 5, 800, 1.3).
carbon_intensity(n1, 0.4).
carbon_intensity(n2, 0.2).
carbon_intensity(n3, 0.1).

% Core operational/production kgCO2eq/GB: Ficher et al. (2021), Table III.
% These include the study's electricity factor/PUE; do not apply them again.
% Assume a 700 km reference distance for both Montpellier profiles.
routeProfile(renater_montpellier_peak,    0.000793, 0.000493).
routeProfile(renater_montpellier_offpeak, 0.001400, 0.000493).

% Synthetic distances in km.
route(n1, n2, 350, renater_montpellier_peak).
route(n2, n1, 350, renater_montpellier_peak).
route(n1, n3, 700, renater_montpellier_peak).
route(n3, n1, 700, renater_montpellier_peak).
route(n2, n3, 1050, renater_montpellier_peak).
route(n3, n2, 1050, renater_montpellier_peak).
