Centralized mock data lives here.

One module per domain (providers, resources, recipients, partners, hubs,
matching, operations, analytics, predictions, notifications). Pages never
import these directly — they go through `src/services/*`, so replacing mocks
with real API calls is a change in one place.

Anything predictive must be labelled as simulated in the UI.
