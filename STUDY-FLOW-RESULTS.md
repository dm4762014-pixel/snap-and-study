# Snap & Study — verified study flow

Checked on Windows on 6 November 2026, in the existing `D:\macropro` project.

## Working demo

Open **http://127.0.0.1:8502** on this laptop. The running browser tab is left at
the real revision recap. The local address is not accessible to Academy reviewers.

To start again, run this from the project directory:

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

Use a free port if another copy is already running. After editing imported
modules, restart your own Streamlit process if hot reload retains a stale import.
Do not stop unrelated Python processes. Credentials stay in the existing private
`.streamlit/secrets.toml`; they are excluded from the source archive.

## Main problems fixed

1. **Telegram prevented students from starting.** A numeric chat ID was mandatory
   even for people who only wanted an explanation or downloadable recap. It is
   now optional. Students can add or correct it in the sidebar later.
2. **Session history and photos grew without a bound.** The app now allows 12
   successful study messages and a cumulative 15 MiB of photos per session.
   Individual photos remain limited to 10 MiB. Server-side checks run before
   provider calls, and recap creation remains available at the message limit.
   No earlier lesson is silently discarded.
3. **Recaps lost their paragraph breaks.** Preview, downloaded text and Telegram
   payload now preserve useful line breaks.
4. **Delivery status ignored the destination.** A recap's last confirmed delivery
   is now tied to its chat ID, so changing the destination does not incorrectly
   mark that destination as already sent.
5. **Accidental interruptions and unbounded responses.** Chat submission disables
   the input while processing; tutoring and recap calls have a 2,048-token output
   budget. The shared client cache also has a two-entry limit.

These are per-session limits, not a global quota, a hard OS RAM cap or a public
deployment security review. Browser upload-extension filters are supplemented by
server-side image validation; extension filters alone are not a security boundary.
[Streamlit chat input documentation](https://docs.streamlit.io/develop/api-reference/chat/st.chat_input)

## Real browser study session

The app used the existing real Gemini connection and its default
`gemini-3.5-flash` model. No model responses were mocked or edited in this session.
The student questions and photo were deliberately scripted test material, not a
trial with a real student.

| Stage | What was tested | Observed result |
|---|---|---|
| Start | Name and AI-processing consent, no Telegram ID | Study session opened |
| Photo + hint | Uploaded a synthetic photo showing `2/3 + 1/6 = 3/9`, asking for a hint | Read the calculation, explained the denominator mistake, withheld the final sum |
| Follow-up | Proposed `4/6 + 1/6 = 5/6`, referring to the earlier photo | Confirmed the answer and explained keeping the common denominator |
| Quiz | Requested one question, `1/4 + 1/2`, without its answer | Asked that question and waited |
| Wrong answer | Deliberately proposed `2/6` by adding denominators | Rejected the reasoning and guided another attempt without immediately revealing the final answer |
| Corrected answer | Proposed `1/4 + 2/4 = 3/4` | Confirmed the corrected answer |
| Recap | Created a recap after the five study messages | Included the topic, actual mistakes, corrections, solved examples and a next exercise |
| Download | Downloaded the recap through the browser | 1,111 characters, line breaks retained; downloaded text exactly matched the preview |

This browser session made five tutoring generations plus one recap generation.
A separate initial real provider check also returned a correct short fraction
hint. The evidence file contains the unedited visible browser snapshots. A few
basic fraction examples do not establish overall answer accuracy, learning
improvement, handwriting recognition quality or curriculum coverage.

## Automated checks

All **16 tests passed** using:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite includes native Streamlit AppTest checks and pure service checks.
Gemini and Telegram are **mocked in this suite**. Checks cover onboarding/reset,
photo/text history, mode forwarding, optional Telegram and later destination
changes, failed calls without automatic retries, retry/discard, empty answers,
recap formatting, server-side bounds, delivery errors and private error messages.

Dependency consistency (`pip check`), Python compilation and `git diff --check`
also passed. A stale import appeared while the development server was hot
reloading changed modules. Only the verified process started for this test was
restarted; the final real browser session ran on the restarted server.

## Telegram boundary

**No real Telegram message was sent during this verification.** The no-ID study
flow intentionally leaves sending disabled. Payload, failure and duplicate-button
handling were tested with mocks. Earlier historical delivery results are not
presented as a fresh delivery check. A Telegram API acceptance would establish
message creation, not that someone read the recap.

## Academy project comparison

| Dimension | Snap & Study | Aegis |
|---|---|---|
| Main task | Help a student work through material, practise and keep a recap | Manage local AI requests under resource pressure |
| Demo clarity | A complete photo-to-hint-to-quiz-to-recap story | A model call, exact cache hit, throttled burst and telemetry |
| Current evidence | Real browser study flow plus 15 automated tests | Recorded real laptop benchmark plus 74 project tests, including earlier diagnostics |
| Main uncertainty | Added value over general AI assistants and real student usefulness | Developer demand and behaviour under sustained workloads |
| What remains unproven | Learning outcomes, broad accuracy, adoption and current public deployment | Production readiness, broad model quality, multi-node operation and adoption |

**Recommendation:** Snap & Study is the stronger candidate for the main video
for this student's application because its task and outcome are easier to show
and explain. This is an assessment, not a prediction of admission. Aegis is useful
supporting evidence of systems work. The test counts measure different scopes
and should not be used to rank the projects.

Snap & Study's present distinction is its connected learning workflow: photo,
hint, contextual follow-up, quiz feedback and an exportable recap. We have not
established that this is sufficiently valuable compared with existing assistants
for students to adopt it. The highest-value next step is one genuine student
trial: record the student's difficulty, whether the hint helped, the wrong-answer
feedback, and what they would change. Obtain permission before recording or
sharing anyone's personal study material.

## Honest contribution statement

Substantial implementation, debugging and the recorded automated/browser testing
were performed by Codex. The user's decisions and learning should be described
specifically and separately. Do not claim independently written code, independent
test execution, real student adoption or improved grades without evidence.

Before recording the Academy video, the applicant should personally walk through
one problem and explain the difference between a hint, a solved answer, retained
conversation context and a recap. Add a truthful personal reason for building the
tool and for attending the Academy. This report is evidence, not a personal essay
to paste into the application.

## Evidence and changes

- `artifacts/live-study-flow.json`: real browser snapshots and review checks.
- `artifacts/live-study-recap.txt`: actual downloaded recap.
- `artifacts/live-study-demo.png`: real browser screenshot.
- `artifacts/study-card.png`: synthetic input used for the photo test.
- `artifacts/automated-tests.txt`: 16 passing tests.
- `artifacts/provider-check.json`: initial real provider check.
- Changed source: `app.py`, `services.py`, `tests/test_project.py`, `README.md`.
- Added documentation: `STUDY-FLOW-RESULTS.md`.

No public deployment, external publication, Git push, Academy submission or
message delivery was performed in this task. The source package needs its own
private Gemini configuration on another computer; no credentials are bundled.

## Three-project portfolio follow-up

Added a full study-session Markdown download that needs no extra AI request.
A fresh real browser question about `1/4 + 1/2` was answered, then the session
file was downloaded and inspected. It retained the question/response and omitted
the personalized onboarding welcome. Photos are represented by an omission note,
not embedded. The actual downloaded file is `artifacts/live-study-session.md`.
This export is additional to the previously recorded five-message study flow.
