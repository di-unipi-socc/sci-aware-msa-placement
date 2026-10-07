% Synthetic cloud-edge scenario. Distances approximate terrestrial routes.
% Carbon quantities use kgCO2eq; capacities and intensities are plausible inputs,
% not measurements of the named locations.

node(pisa_edge,       tor(1.5,3,0.8,0.8), 0.0040, 5, 110, 1.12).
node(florence_edge,   tor(2.0,4,1.0,1.0), 0.0045, 5, 145, 1.15).
node(bologna_edge,    tor(2.5,5,1.2,1.2), 0.0050, 5, 185, 1.18).
node(rome_edge,       tor(2.0,4,1.0,1.0), 0.0048, 5, 160, 1.20).
node(milan_regional,  tor(3.5,8,1.8,1.8), 0.0065, 5, 360, 1.22).
node(zurich_regional, tor(3.0,7,1.5,1.5), 0.0060, 6, 330, 1.18).
node(paris_cloud,     tor(4.0,8,2.0,2.0), 0.0075, 5, 480, 1.16).
node(frankfurt_cloud, tor(4.0,8,2.0,2.0), 0.0075, 5, 500, 1.20).

carbon_intensity(pisa_edge, 0.29).
carbon_intensity(florence_edge, 0.21).
carbon_intensity(bologna_edge, 0.36).
carbon_intensity(rome_edge, 0.33).
carbon_intensity(milan_regional, 0.19).
carbon_intensity(zurich_regional, 0.08).
carbon_intensity(paris_cloud, 0.07).
carbon_intensity(frankfurt_cloud, 0.31).

% Operational/production kgCO2eq/GB: Ficher et al. (2021), Table III.
% networkIntensity/4 scales these 700 km reference values by route distance.
routeProfile(renater_montpellier_peak, 0.000793, 0.000493).

route(pisa_edge, florence_edge, 85, renater_montpellier_peak).
route(florence_edge, pisa_edge, 85, renater_montpellier_peak).
route(pisa_edge, bologna_edge, 180, renater_montpellier_peak).
route(bologna_edge, pisa_edge, 180, renater_montpellier_peak).
route(pisa_edge, rome_edge, 355, renater_montpellier_peak).
route(rome_edge, pisa_edge, 355, renater_montpellier_peak).
route(pisa_edge, milan_regional, 280, renater_montpellier_peak).
route(milan_regional, pisa_edge, 280, renater_montpellier_peak).
route(pisa_edge, zurich_regional, 520, renater_montpellier_peak).
route(zurich_regional, pisa_edge, 520, renater_montpellier_peak).
route(pisa_edge, paris_cloud, 1050, renater_montpellier_peak).
route(paris_cloud, pisa_edge, 1050, renater_montpellier_peak).
route(pisa_edge, frankfurt_cloud, 950, renater_montpellier_peak).
route(frankfurt_cloud, pisa_edge, 950, renater_montpellier_peak).

route(florence_edge, bologna_edge, 105, renater_montpellier_peak).
route(bologna_edge, florence_edge, 105, renater_montpellier_peak).
route(florence_edge, rome_edge, 275, renater_montpellier_peak).
route(rome_edge, florence_edge, 275, renater_montpellier_peak).
route(florence_edge, milan_regional, 305, renater_montpellier_peak).
route(milan_regional, florence_edge, 305, renater_montpellier_peak).
route(florence_edge, zurich_regional, 530, renater_montpellier_peak).
route(zurich_regional, florence_edge, 530, renater_montpellier_peak).
route(florence_edge, paris_cloud, 1150, renater_montpellier_peak).
route(paris_cloud, florence_edge, 1150, renater_montpellier_peak).
route(florence_edge, frankfurt_cloud, 975, renater_montpellier_peak).
route(frankfurt_cloud, florence_edge, 975, renater_montpellier_peak).

route(bologna_edge, rome_edge, 380, renater_montpellier_peak).
route(rome_edge, bologna_edge, 380, renater_montpellier_peak).
route(bologna_edge, milan_regional, 215, renater_montpellier_peak).
route(milan_regional, bologna_edge, 215, renater_montpellier_peak).
route(bologna_edge, zurich_regional, 450, renater_montpellier_peak).
route(zurich_regional, bologna_edge, 450, renater_montpellier_peak).
route(bologna_edge, paris_cloud, 1070, renater_montpellier_peak).
route(paris_cloud, bologna_edge, 1070, renater_montpellier_peak).
route(bologna_edge, frankfurt_cloud, 800, renater_montpellier_peak).
route(frankfurt_cloud, bologna_edge, 800, renater_montpellier_peak).

route(rome_edge, milan_regional, 570, renater_montpellier_peak).
route(milan_regional, rome_edge, 570, renater_montpellier_peak).
route(rome_edge, zurich_regional, 685, renater_montpellier_peak).
route(zurich_regional, rome_edge, 685, renater_montpellier_peak).
route(rome_edge, paris_cloud, 1420, renater_montpellier_peak).
route(paris_cloud, rome_edge, 1420, renater_montpellier_peak).
route(rome_edge, frankfurt_cloud, 1200, renater_montpellier_peak).
route(frankfurt_cloud, rome_edge, 1200, renater_montpellier_peak).

route(milan_regional, zurich_regional, 280, renater_montpellier_peak).
route(zurich_regional, milan_regional, 280, renater_montpellier_peak).
route(milan_regional, paris_cloud, 850, renater_montpellier_peak).
route(paris_cloud, milan_regional, 850, renater_montpellier_peak).
route(milan_regional, frankfurt_cloud, 650, renater_montpellier_peak).
route(frankfurt_cloud, milan_regional, 650, renater_montpellier_peak).

route(zurich_regional, paris_cloud, 650, renater_montpellier_peak).
route(paris_cloud, zurich_regional, 650, renater_montpellier_peak).
route(zurich_regional, frankfurt_cloud, 410, renater_montpellier_peak).
route(frankfurt_cloud, zurich_regional, 410, renater_montpellier_peak).

route(paris_cloud, frankfurt_cloud, 570, renater_montpellier_peak).
route(frankfurt_cloud, paris_cloud, 570, renater_montpellier_peak).
