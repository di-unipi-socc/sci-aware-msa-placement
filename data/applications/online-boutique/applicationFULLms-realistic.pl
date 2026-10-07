% Synthetic but plausible Online Boutique workload.
% rr(CPU cores, RAM GB, inbound Gbit/s, outbound Gbit/s).
% TiR is the fraction of one reporting year during which the service runs.

application(onlineBoutique,
    [frontend, checkout, currency, email, payment, recommendation, shipping, ad, cart, product_catalog],
    [home, product, addToCart, viewCart, emptyCart, placeOrder]).

microservice(frontend,         rr(0.60, 0.768, 0.20, 0.35), 1.00).
microservice(checkout,         rr(0.80, 1.250, 0.12, 0.18), 0.20).
microservice(currency,         rr(0.25, 0.384, 0.05, 0.05), 0.85).
microservice(email,            rr(0.20, 0.384, 0.03, 0.08), 0.10).
microservice(payment,          rr(0.60, 0.768, 0.08, 0.12), 0.18).
microservice(recommendation,   rr(0.75, 1.024, 0.14, 0.16), 0.55).
microservice(shipping,         rr(0.40, 0.512, 0.06, 0.08), 0.25).
microservice(ad,               rr(0.50, 0.768, 0.12, 0.22), 0.45).
microservice(cart,             rr(0.65, 1.024, 0.12, 0.14), 0.70).
microservice(product_catalog,  rr(0.70, 1.024, 0.18, 0.22), 0.80).

% AvgGB is the expected volume transferred per endpoint invocation.
endpoint(home, [
    (frontend, product_catalog, 0.00020),
    (frontend, currency, 0.00002),
    (frontend, cart, 0.00003),
    (frontend, ad, 0.00008)
]).
endpoint(product, [
    (frontend, product_catalog, 0.00035),
    (frontend, currency, 0.00002),
    (product_catalog, recommendation, 0.00012),
    (recommendation, ad, 0.00004)
]).
endpoint(addToCart, [
    (frontend, product_catalog, 0.00003),
    (frontend, cart, 0.00002)
]).
endpoint(viewCart, [
    (frontend, cart, 0.00010),
    (cart, product_catalog, 0.00004),
    (cart, shipping, 0.00002),
    (frontend, currency, 0.00002)
]).
endpoint(emptyCart, [
    (frontend, cart, 0.00001)
]).
endpoint(placeOrder, [
    (frontend, checkout, 0.00006),
    (checkout, cart, 0.00004),
    (checkout, product_catalog, 0.00003),
    (checkout, currency, 0.00001),
    (checkout, shipping, 0.00002),
    (checkout, payment, 0.00001),
    (checkout, email, 0.000005)
]).

probability(home, 0.30).
probability(product, 0.34).
probability(addToCart, 0.12).
probability(viewCart, 0.16).
probability(emptyCart, 0.03).
probability(placeOrder, 0.05).

% Expected endpoint invocations in one reporting year.
functionalUnits(onlineBoutique, 25000000).
