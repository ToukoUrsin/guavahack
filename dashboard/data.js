/* =============================================================================
 * Second Draft - practitioner dashboard data
 *
 * >>> PLACEHOLDER DATA. NOT REAL PATIENT DATA. <<<
 *
 * Every session below is invented so the dashboard renders and can be demoed.
 * Joel Jussila is the only populated record, at his own request and with his
 * own name; the other nine are fictional people with no sessions.
 *
 * TO SWAP IN THE REAL GUAVA CALLS:
 *   Replace PATIENTS[0].sessions with one object per call, same shape:
 *     { n, date, channel, mode, scene, minutes, note, detail, followup, flag }
 *   note      - one line, shown collapsed
 *   detail    - what happened, shown when the session is opened
 *   followup  - what to pick up next time
 *   Nothing else needs to change; the page derives everything from this array.
 *
 * Never put a real caller's name, number, or identifying detail in this file.
 * ========================================================================== */

const CLINIC = {
  product: "Second Draft",
  role: "Practitioner view",
  clinician: "Dr. R. Salo",
};

const JOEL_SESSIONS = [
  {
    n: 1, date: "2026-06-02", channel: "human", mode: "coach", scene: null, minutes: 50, flag: null,
    note: "Intake. Named the pattern: goes quiet, then resents it.",
    detail:
      "First appointment. Described a pattern going back years: when something bothers him he says nothing, tells himself it is not worth a fight, then carries it for weeks. Offered the April birthday as the example — it went unmarked and he never raised it. Visibly uncomfortable naming his own needs out loud.",
    followup: "He has never said the sentence out loud to anyone. Start there.",
  },
  {
    n: 2, date: "2026-06-05", channel: "ai", mode: "coach", scene: null, minutes: 12, flag: null,
    note: "First call. Talked it through, declined rehearsal.",
    detail:
      "Used the call to think out loud rather than practise. Circled one worry repeatedly: that saying it will land as an accusation. Declined the offer to rehearse and the agent did not push.",
    followup: "Declining was right at this stage. He needs the words before the scene.",
  },
  {
    n: 3, date: "2026-06-09", channel: "ai", mode: "rehearsal", scene: "Alex", minutes: 18, flag: null,
    note: "Opened with an apology. Never stated the need.",
    detail:
      "First rehearsal with the Alex persona. Opened with “sorry to bring this up” and spent most of the call managing her feelings instead of stating his own. Ran out of call before naming what he wanted. Went quiet twice when she got short with him.",
    followup: "The apology opener is the whole pattern in miniature. Name it next session.",
  },
  {
    n: 4, date: "2026-06-12", channel: "ai", mode: "rehearsal", scene: "Alex", minutes: 21, flag: null,
    note: "Got to the need at minute 14. Backed off when she pushed.",
    detail:
      "Reached the actual sentence at minute 14, then immediately softened it into “but it’s fine, honestly.” When the persona pushed back he retreated to logistics — schedules, who does what — and never returned to the point.",
    followup: "He can say it. He cannot yet hold it. Work on staying in it after the sentence.",
  },
  {
    n: 5, date: "2026-06-16", channel: "human", mode: "coach", scene: null, minutes: 50, flag: null,
    note: "Reviewed two rehearsals. Set the two-minute goal.",
    detail:
      "Listened back to the two rehearsals together. He recognised the apology opener himself without prompting, which he found uncomfortable but useful. Agreed a concrete target: state the need inside the first two minutes, before he can talk himself out of it.",
    followup: "Goal agreed with him, not imposed. Hold him to the two minutes.",
  },
  {
    n: 6, date: "2026-06-19", channel: "ai", mode: "rehearsal", scene: "Alex", minutes: 16, flag: null,
    note: "Stated it at minute 3. Voice tightened under pushback.",
    detail:
      "Close to the two-minute target. Said it plainly and did not apologise first. Voice went tight and fast when the persona questioned whether he was being fair, but he stayed in the conversation rather than leaving it.",
    followup: "Real step. Note the physical tell — his voice speeds up before he retreats.",
  },
  {
    n: 7, date: "2026-06-23", channel: "ai", mode: "rehearsal", scene: "Alex", minutes: 19, flag: null,
    note: "Persona pushed harder. Went defensive twice.",
    detail:
      "Difficulty raised at his own request. Twice moved from stating his need to defending his record, listing things he had done around the house. Recovered on his own the second time without prompting.",
    followup: "Defensiveness appears when she implies he is being unfair. Worth exploring where that comes from.",
  },
  {
    n: 8, date: "2026-06-26", channel: "ai", mode: "safety", scene: "Alex", minutes: 7, flag: "safety",
    note: "Distress language mid-scene. Persona dropped, routed to human support.",
    detail:
      "Mid-scene the content moved from the rehearsal to his own state, and he used language the safety layer flagged as real distress rather than roleplay. The agent dropped the Alex persona immediately, stopped the rehearsal, said plainly that it could not connect him to a person or provide crisis care, and gave the 988 line along with the suggestion to contact someone who could be with him. The call ended shortly after. No return to roleplay in the session.",
    followup: "Escalation handled as designed. Follow up in person before any further rehearsal.",
  },
  {
    n: 9, date: "2026-06-30", channel: "human", mode: "coach", scene: null, minutes: 50, flag: null,
    note: "Unpacked the escalation. Agreed to lower scene intensity.",
    detail:
      "Talked through what happened on the call. He was not in crisis, but the scene had got close to something real about his father rather than his partner. Agreed to lower intensity and to keep the father material for later, with the practitioner present.",
    followup: "The father thread is live. Do not let a persona reach it unsupervised.",
  },
  {
    n: 10, date: "2026-07-03", channel: "ai", mode: "coach", scene: null, minutes: 14, flag: null,
    note: "Coaching only, no roleplay. Rebuilt confidence.",
    detail:
      "Deliberately no rehearsal. Used the call to talk about what he wants from the next conversation with Alex, and to reset after the escalation. Ended in better shape than he started.",
    followup: "Confidence returning. Ready to rehearse again at low intensity.",
  },
  {
    n: 11, date: "2026-07-07", channel: "ai", mode: "rehearsal", scene: "Alex", minutes: 17, flag: null,
    note: "Softer scene. Stayed in it the whole time.",
    detail:
      "Low-intensity scene, persona warmer and less challenging. Stayed present for the whole call with no retreat to logistics. Said the sentence early and then let a silence sit instead of filling it.",
    followup: "Letting the silence sit is new. That is the skill, not the sentence.",
  },
  {
    n: 12, date: "2026-07-10", channel: "ai", mode: "rehearsal", scene: "Alex", minutes: 20, flag: null,
    note: "First time he repaired after a bad line.",
    detail:
      "Said something clumsy — implied she was keeping score — noticed it himself, and repaired it in the moment rather than defending it or going quiet. First time he has done this in any rehearsal.",
    followup: "Repair in the moment is worth more than a clean run. Tell him that.",
  },
  {
    n: 13, date: "2026-07-14", channel: "ai", mode: "rehearsal", scene: "Manager", minutes: 15, flag: null,
    note: "New scene: asking for a raise. Calm, but undersold it.",
    detail:
      "New counterpart. Noticeably calmer than in the partner scenes — the emotional stakes are lower for him. Undersold his own case and accepted the first deflection to budget without pushing on it.",
    followup: "Same avoidance, lower temperature: he asks once and lets it go.",
  },
  {
    n: 14, date: "2026-07-17", channel: "human", mode: "coach", scene: null, minutes: 50, flag: null,
    note: "Transfer of skill across scenes discussed.",
    detail:
      "Discussed that the same avoidance shows up at work and at home. He had not connected the two before. Found the work example easier to look at directly because it felt less personal.",
    followup: "Use the manager scene as the low-stakes way into the same pattern.",
  },
  {
    n: 15, date: "2026-07-21", channel: "ai", mode: "rehearsal", scene: "Manager", minutes: 18, flag: null,
    note: "Named a number and did not discount it.",
    detail:
      "Stated a figure and, through the pause that followed, did not soften or withdraw it. Handled the budget deflection by asking what would need to change for it to be possible, rather than accepting it as an answer.",
    followup: "Holding the number is the same skill as holding the need. Make the link explicit.",
  },
  {
    n: 16, date: "2026-07-28", channel: "ai", mode: "rehearsal", scene: "Alex", minutes: 19, flag: null,
    note: "Held the ask through two rounds of pushback.",
    detail:
      "Back to the partner scene at full intensity. Stated the need early and held it through two rounds of pushback without defending his record and without retreating to logistics.",
    followup: "This is what the goal set at session 5 looks like when it is met.",
  },
  {
    n: 17, date: "2026-08-04", channel: "ai", mode: "rehearsal", scene: "Father", minutes: 22, flag: null,
    note: "Hardest scene yet. Boundary collapsed at the end.",
    detail:
      "First father scene, agreed in advance with the practitioner. Held for most of the call, then when the persona used humour to change the subject he laughed along and dropped the point entirely. Noticeably flat for the last few minutes.",
    followup: "Humour is the exit route. Name it before the next father scene.",
  },
  {
    n: 18, date: "2026-08-11", channel: "ai", mode: "rehearsal", scene: "Father", minutes: 21, flag: null,
    note: "Held it. Did not apologise for having the boundary.",
    detail:
      "Second father scene. The humour deflection came again and this time he named it — said he noticed the subject changing and returned to his point. Did not apologise for having the boundary, which he has done in every previous father or partner scene.",
    followup: "Significant. The thing he could not do at session 17 he did here.",
  },
  {
    n: 19, date: "2026-08-18", channel: "human", mode: "coach", scene: null, minutes: 50, flag: "milestone",
    note: "Practitioner review. Ready for the real conversation.",
    detail:
      "Reviewed the whole arc from intake. He can state a need, stay in the conversation after saying it, and return to it when deflected. Agreed he is ready to have the real conversation with his partner. Also talked about what a bad outcome would mean, and that rehearsal does not guarantee the result.",
    followup: "Ready. Expect a debrief session afterwards regardless of how it goes.",
  },
  {
    n: 20, date: "2026-08-25", channel: "ai", mode: "rehearsal", scene: "Alex", minutes: 16, flag: null,
    note: "Final rehearsal before the real one. Clean run.",
    detail:
      "Short final run at full intensity. Stated the need inside ninety seconds, stayed through pushback, and closed by asking her what she needed — which he has not done in any prior rehearsal.",
    followup: "Nothing further to rehearse. Book the debrief.",
  },
];

const PATIENTS = [
  {
    id: "joel-jussila",
    name: "Joel Jussila",
    since: "2026-06-02",
    focus: "Avoids confrontation with partner",
    came_for:
      "Goes quiet when something bothers him, then resents it weeks later. Has never told his partner he feels unappreciated, and a birthday went unmarked in April without him saying anything.",
    goal:
      "Say “I feel unappreciated” out loud, in the first two minutes, and stay in the conversation when she pushes back.",
    scenes: [
      { name: "Alex", who: "Partner", behavior: "Hurt, a little distant. Pushes back, needs to feel heard." },
      { name: "Manager", who: "Manager at work", behavior: "Friendly, deflects to budget, waits out silences." },
      { name: "Father", who: "Father", behavior: "Warm but dismissive. Changes the subject with humour." },
    ],
    sessions: JOEL_SESSIONS,
  },
  { id: "maya-okonkwo",   name: "Maya Okonkwo",     since: null, focus: null, came_for: null, goal: null, scenes: [], sessions: [] },
  { id: "tomas-lindqvist",name: "Tomás Lindqvist", since: null, focus: null, came_for: null, goal: null, scenes: [], sessions: [] },
  { id: "priya-raman",    name: "Priya Raman",      since: null, focus: null, came_for: null, goal: null, scenes: [], sessions: [] },
  { id: "daniel-abebe",   name: "Daniel Abebe",     since: null, focus: null, came_for: null, goal: null, scenes: [], sessions: [] },
  { id: "sofia-marchetti",name: "Sofia Marchetti",  since: null, focus: null, came_for: null, goal: null, scenes: [], sessions: [] },
  { id: "henrik-dahl",    name: "Henrik Dahl",      since: null, focus: null, came_for: null, goal: null, scenes: [], sessions: [] },
  { id: "amara-nwosu",    name: "Amara Nwosu",      since: null, focus: null, came_for: null, goal: null, scenes: [], sessions: [] },
  { id: "leo-fontaine",   name: "Leo Fontaine",     since: null, focus: null, came_for: null, goal: null, scenes: [], sessions: [] },
  { id: "ines-varga",     name: "Ines Varga",       since: null, focus: null, came_for: null, goal: null, scenes: [], sessions: [] },
];
