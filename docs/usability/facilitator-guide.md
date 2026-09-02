# Facilitator Guide

## Before the session

1. Verify the V1.5 stack and the `product` catalog; it must list only `cn_300750 / 2024H1`.
2. Complete one dry run and confirm that conclusion, facts, calculations, official evidence,
   counter evidence, limitations, monitoring and trace render from API artifacts.
3. Start from the Research page with no result displayed. Do not open Quality Lab.
4. Provide the privacy notice, record consent and assign a non-identifying pseudonym.
5. Copy the schema-valid session template into ignored local storage.

## During the session

- Read the scenario and tasks without demonstrating the interface.
- Ask neutral prompts such as “What are you looking for?” or “What do you expect that to do?”
- Do not point to the correct control, evidence item, limitation or monitoring item.
- Intervene only for a genuine technical failure; record the intervention and do not count the
  affected task as independently completed.
- Preserve hesitation, disagreement and negative feedback. Do not translate them into success.

## After the session

1. Mark the six contract outcomes from direct observation.
2. Record short feedback without identity or private financial information.
3. Set `completed_at` and `status: completed`, or `withdrawn` if requested.
4. Validate the record against `schemas/v1.5/human-usability-session.schema.json`.
5. Reset by returning to Research and reloading the page; use a new idempotency key and pseudonym
   for the next person.

The facilitator may fix technical defects between sessions, but must record the tested commit for
each session in the private notes. Sessions across materially different interfaces are reported
separately.
