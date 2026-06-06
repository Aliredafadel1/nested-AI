---
name: nest-specify
description: Create a NestAI feature spec using the spec-kit SDD workflow. Run this before planning any new feature or module change.
disable-model-invocation: true
---
Create a spec for: $ARGUMENTS

Steps:

1. Read `specs/all_modules.yaml` to understand existing module contracts and endpoints.
2. Read `.specify/memory/constitution.md` for project principles.
3. Ask clarifying questions before writing — do not skip this:
   - Which of the 10 modules does this feature touch?
   - What is the user-facing outcome?
   - Student role, landlord role, or both?
   - Any Lebanon-specific context (electricity schedule, currency, Arabic/French/English)?
   - Any new LLM calls needed? If so, which reasoning tier fits?
   - What does "done" look like — what can a user do that they couldn't before?

4. Create `specs/<kebab-case-feature-name>/spec.md` with these sections:
   - **Summary**: one paragraph — what it is and why it matters for Lebanese students
   - **User stories**: `As a <student|landlord>, I want <action> so that <outcome>`
   - **Acceptance criteria**: checkbox list — each item is observable and testable
   - **Out of scope**: explicit list of what this spec does NOT cover
   - **Module impact**: list which of the 10 modules are affected and how
   - **Data model changes**: any new columns or tables (with SQL types)
   - **API surface**: new endpoints or changes to existing ones (method, path, request, response)
   - **AI/LLM involvement**: tier (free/cheap/powerful), task name, where in the flow
   - **Security considerations**: auth requirements, rate limits, file validation if any
   - **Lebanon-specific considerations**: generator hours, dual-currency prices, multilingual text

5. End the spec with: *"Run `/nest-plan` to generate the technical implementation plan."*
