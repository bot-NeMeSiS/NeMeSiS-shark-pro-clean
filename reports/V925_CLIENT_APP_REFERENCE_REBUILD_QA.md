# V925 Client App Reference Rebuild QA

## Result

The client center keeps its existing authenticated behavior and now reads from the V925 safe sports contexts. The visible structure prioritizes:

- Madrid time and current membership.
- SHARK safe-mode state.
- Quick access to calendar, live, picks, SHARK, Telegram and profile.
- Real counts when data exists and explicit safe states when it does not.
- A clear next action instead of decorative empty space.

The V923 redirect-safe behavior for unauthenticated `/app` and `/profile` remains in place. Client navigation remains separate from admin navigation.

No fake activity, membership, sports or payment values were added.
