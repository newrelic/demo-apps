// Fixed pool of virtual player identities. Each userId maps 1:1 to an
// appVersion, simulating a gradual/canary client rollout across users.
export default [
  { userId: 'player-aria-01', appVersion: '2.4.0' },
  { userId: 'player-milo-02', appVersion: '2.4.1' },
  { userId: 'player-priya-03', appVersion: '2.5.0-canary' },
  { userId: 'player-devon-04', appVersion: '2.3.2' },
  { userId: 'player-sasha-05', appVersion: '2.5.0-canary' },
];
