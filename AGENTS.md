# Working in Podcut Flow

For **editing a user's podcast**, read START_HERE.md and the podcut-flow skill. Ask for the episode folder if missing. Preserve choices and source media. Follow the user's requested delivery; Premiere-only work must not trigger a full video render.

For **installing the workflow**, follow docs/SETUP.md and complete missing dependency/integration setup, reusing working tools. Installation alone does not require an episode folder. Do not stop at listing downloads when the user has asked you to perform setup.

For **developing this repository**, inspect relevant code, make the change, run meaningful tests with `python -m pytest`, and update affected documentation. Do not start episode intake for a coding task. Keep dependencies modest and processing local. Use synthetic media in tests. Do not add real recordings, transcripts, personal filesystem paths, local-auth files or secrets. Independent source lanes, stable timebases, stale-output rejection and honest delivery labels are required behavior.

Skill location: `.agents/skills/podcut-flow/SKILL.md`. Detailed setup and implementation usage are under `docs/`.
