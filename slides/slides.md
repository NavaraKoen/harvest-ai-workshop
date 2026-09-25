---
# try also 'default' to start simple
theme: seriph
# random image from a curated Unsplash collection by Anthony
# like them? see https://unsplash.com/collections/94734566/slidev
background: https://images.unsplash.com/photo-1737644467636-6b0053476bb2?q=80&w=2572&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D
# some information about your slides (markdown enabled)
title: Agentic Engineering Workshop
class: text-center
# https://sli.dev/features/drawing
drawings:
  persist: false
# slide transition: https://sli.dev/guide/animations.html#slide-transitions
transition: slide-left
# enable Comark Syntax: https://comark.dev/syntax/markdown
comark: true
# duration of the presentation
duration: 35min
---

# Agentic Engineering masterclass

## Harvest

25-09-2026

---

# Timetable

| Tijd           | Onderdeel                            |
| -------------- | ------------------------------------ |
| 13:00 - 13:20  | Intro  **< Hier zijn we nu**         |
| 13:20 - 13:35  | Agentic Engineering - intro opdracht |
| 13:35 - 14:00  | Eerste opdrachtje                    |
| 14:00 - 14:15  | Pauze                                |
| 14:15 - 15:45  | Hackathon                            |
| 15:45 - 16:15  | Demos + wrap-up                      |
| 16:15 - donker | Borrel                               |

---
layout: two-cols
---

# Introductie

- Koen Griffioen
- Software Engineering Consultant @ BBTG
- "Quality Assurance Engineer" @ Eneco
- Privé
  - Getrouwd, dochter van 2,5
  - Gamer
  - Muziekliefhebber
  - Ik ren
- Achtergrond
  - Master Computer Science (Leiden)
  - 3 jaar Capgemini als Consultant en trainer
  - (over 6 dagen) 6 jaar in dienst bij NAVARA / BBTG

::right::

<div class="flex items-center justify-center h-full">
  <img src="/img/koen.png" class="w-80 rounded-md shadow" />
</div>

---

# Mijn reis tot zover
- Capgemini
  - Frontends, Angular
  - Backend, C# / .NET
  - Trainer voor Software Engineering (Full-stack, Java)
- via NAVARA @Essent
  - Frontend (Angular) 2022-2024
  - Backend (AWS serverless) 2024-2025
  - Durability (Temporal) 2025-2026
- Via NAVARA @Eneco
  - "Quality Assurance Engineer" in een OT team
  - Megabatterijen
- Trainer


---
layout: two-cols
---

# Essent - oorspronkelijke situatie
Van hopeloos verouderde integratie naar een TypeScript monorepo

- Axway => Tibco low-code => SAP
- TypeScript frontends in monorepo
- "Doet ie het wel of doet ie het niet"

::right::

<div class="flex items-center justify-center h-full">
  <img src="/img/callcenter.png" class="w-80 rounded-md shadow" />
</div>

---

# Essent - oorspronkelijke situatie
Van hopeloos verouderde integratie naar een TypeScript monorepo

```mermaid
graph LR
  User[User] --> Gateway[Axway API Gateway]
  Gateway --> Functional[Tibco Functional Service]
  Functional --> Entity[Tibco Entity Service]
  Entity --> SAP[SAP]
```

"Oeps, er is iets misgegaan"

---
transition: slide-up
---

# Doorlooptijd per wijziging

```mermaid
graph LR
  User[User] -->|3 weken| Gateway[Axway API Gateway]
  Gateway -->|3 weken| Functional[Tibco Functional Service]
  Functional -->|3 weken| Entity[Tibco Entity Service]
  Entity -->|4 weken| SAP[SAP]
```

- Axway API: **3 weken**
- Tibco Functional Service: **3 weken**
- Tibco Entity Service: **3 weken**
- SAP: **4 weken**
- **Totaal: 13 weken** voor een end-to-end wijziging

---

# Essent - onbereikbaar?

<div class="flex items-center justify-center h-full">
  <img src="/img/essent_onbereikbaar.png" class="w-90 shadow" />
</div>

---
layout: two-cols
---

# Enter NAVARA

- PoC met MonoRepo platform + AWS Serverless deployments
- Doorlooptijden van < 30 minuten
- Monitoring out of the box
- Alerting out of the box
- Configuration as code
- "Eindeloze" schaalbaarheid
- Services as code => transparency
- Standardization of code
- Linting
- _Unit tests??_
- _Integration tests???_



---

# Nieuwe Architectuur

```mermaid
graph LR
  User[User] --> Gateway["AWS API Gateway (deployed from code)"]
  Gateway --> Functional["AWS Lambda Functional Service (deployed from code)"]
  Functional --> SAP

  subgraph Minuten ["⏱️ Valideert en deployed in minuten, niet weken"]
    Gateway
    Functional
  end
```

```ts
export const getCustomerV1 = async (id: string) => {
  await sapClient.connect();
  const result = await sapClient.getCustomer(id);
  const mapped = result.map((c) => ({ id: c.id, name: c.name }));
  return mapped;
};
```
---

# Operatie "Team Lambda"

Platform engineering

Service conversion flow

<v-click>

```mermaid
graph LR
  A[Download all files related to a service] --> B[Recreate service]
  B --> C[Replay production requests through old and new services]
  C -->|Differences found| B
  C -->|No differences| D[Start scaling]
  D -->|Something wrong| B
  D -->|OK| E[100%]
```
</v-click>

---

# Scale

- 150 services*
- 10 teams*
- 1,5 jaar
- 0% Tibco :)
- 100% TypeScript + AWS Serverless met tests


---

# Next step: workflows

DDD zit niet altijd mee

<v-clicks>

- Event-driven setup
- Geen observability
- Geen retries
- Complete chaos

</v-clicks>

<div v-click class="absolute inset-0 flex items-center justify-center">
  <img src="/img/thisisfinefire.png" class="w-full max-w-180 rounded-md shadow-lg" />
</div>

---

<div class="absolute inset-0 flex items-center justify-center">
  <img src="/img/Temporal_I_got_this.png" class="h-full rounded-md shadow-lg" />
</div>

---
layout: quote
---
# Wat is Temporal?

Durable execution

---

# Hoe ziet een Temporal-driven workflow eruit?

```ts
async function processOrder(order: Order): Promise<void> {
  // Step 1: charge the customer
  const payment = await stripe.charges.create({
    amount: order.totalCents,
    customer: order.customerId,
  });

  // Step 2: fulfill the order in the warehouse system
  await warehouseApi.createPickingTask({
    orderId: order.id,
    items: order.items,
  });

  // Wait two hours before sending the notification for some reason
  wf.sleep('2 hours');

  // Step 3: notify the customer
  await sendEmail({
    subject: "Your order is confirmed!",
    body: `Hi ${order.customerName}, we've received order #${order.id}.`,
  });
}
```

---

# Waarom gebruiken de grote AI bedrijven zoals OpenAI Temporal?

- Een gesprek of een complexe taak kun je zien als een langlopende workflow
- Agents die met andere agents werken krijgen te maken met connection drops
- Tools / activiteiten die uitgevoerd moeten worden, kunnen falen of onderbroken worden


---
layout: two-cols
---

# Workshop

Agentic Orchestration workshop: Praten met een LLM

- Introductie op de repo
- Probleemstelling
- Korte demo
- Demo zonder Temporal als Durability platform
- Eerste opdrachtje
- Hackathon!

::right::

<div class="flex flex-col gap-2 items-center justify-center h-full">
  <img src="/img/koen.png" class="w-40 rounded-md shadow" />
  <img src="/img/lars.png" class="w-40 rounded-md shadow" />
  <img src="/img/ifran.png" class="w-40 rounded-md shadow" />
</div>

---

# Timetable

| Tijd           | Onderdeel                                                   |
| -------------- | ----------------------------------------------------------- |
| 13:00 - 13:20  | Intro                                                       |
| 13:20 - 13:35  | Agentic Engineering - intro opdracht  **< Hier zijn we nu** |
| 13:35 - 14:00  | Eerste opdrachtje                                           |
| 14:00 - 14:15  | Pauze                                                       |
| 14:15 - 15:45  | Hackathon                                                   |
| 15:45 - 16:15  | Demos + wrap-up                                             |
| 16:15 - donker | Borrel                                                      |


---

# Praten met een LLM 101

Hoe pak je dat eigenlijk aan?

```
User:  "hey"
Agent: "hey, what can I do for you?"
User:  "wat is het weer in Utrecht?"
Agent: "zonnig, 18 graden"
```

Elke keer opnieuw naar de LLM:

```
<system prompt>
+ "Dit is al gezegd: user: hey | agent: hey, what can I do for you?
   | user: wat is het weer in Utrecht? | agent: zonnig, 18 graden"
+ <nieuwe user message>
```

--- 

# Introductie repo

```
- api -> backend API endpoints
- config -> Tools
- frontend -> Chat user interface
- llm -> Language model broker
- temporal_app -> Temporal workflow -> main chat loop
```

---
layout: center
class: text-center
---

<div class="text-8xl font-bold">DEMO</div>


---

# Timetable

| Tijd           | Onderdeel                                            |
| -------------- | ---------------------------------------------------- |
| 13:00 - 13:20  | Intro                                                |
| 13:20 - 13:35  | Agentic Engineering - intro opdracht                 |
| 13:35 - 14:00  | Eerste opdrachtje              **< Hier zijn we nu** |
| 14:00 - 14:15  | Pauze                                                |
| 14:15 - 15:45  | Hackathon                                            |
| 15:45 - 16:15  | Demos + wrap-up                                      |
| 16:15 - donker | Borrel                                               |

---

# Eerste opdrachtje

Goal: extend the protocol end-to-end (prompt → models → workflow → frontend).

1. `temporal_app/models.py`: add `ASK_CHOICE = "ask_choice"` to `ActionType`.
2. `llm_activities.py`: update the system prompt to document `ask_choice` and require an
   `"options": ["...", "..."]` field alongside `tool_name`/`tool_args` (or a new field).
3. `chat.py` (workflow): handle `ActionType.ASK_CHOICE.value` similarly to `ask_input`, but
   store the offered options in workflow state so the frontend can render buttons.
4. `frontend/index.html`: render option buttons when `action_type == "ask_choice"`, and on click,
   send the choice back via the existing `send_user_input` signal (reuse it — no new signal needed).
5. Update the prompt's flow instructions to use `ask_choice` for "which flight/hotel do you prefer".


---

# Timetable

| Tijd           | Onderdeel                                             |
| -------------- | ----------------------------------------------------- |
| 13:00 - 13:20  | Intro                                                 |
| 13:20 - 13:35  | Agentic Engineering - intro opdracht                  |
| 13:35 - 14:00  | Eerste opdrachtje                                     |
| 14:00 - 14:15  | Pauze                           **< Hier zijn we nu** |
| 14:15 - 15:45  | Hackathon                                             |
| 15:45 - 16:15  | Demos + wrap-up                                       |
| 16:15 - donker | Borrel                                                |