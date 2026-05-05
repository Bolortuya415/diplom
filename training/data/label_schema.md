# Sensitive Content Classifier — Label Schema

## Task Definition
Classify Mongolian text input into one of the following categories to determine
whether the chatbot should respond normally or trigger a safety intervention.

## Labels

| Label | Code | Description | Chatbot Action |
|---|---|---|---|
| safe | 0 | Normal question or statement | Proceed with RAG pipeline |
| hate_speech | 1 | Hatred/hostility toward a group based on gender, ethnicity, disability, etc. | Safety warning + educational response |
| harassment | 2 | Bullying, threats, personal attacks, intimidation | Safety warning + support resources |
| discrimination | 3 | Discriminatory statements about employment, education, access | Educational correction + legal info |
| self_harm | 4 | Indicators of self-harm, suicidal ideation, crisis | Crisis resources + helpline numbers |

## Annotation Guidelines

1. **Read the full text** before assigning a label.
2. **Choose the most specific label** — if text contains both hate_speech and harassment, choose the dominant one.
3. **Context matters** — a question *about* hate speech (e.g., "Үзэн ядалтын яриа гэж юу вэ?") is `safe`, not `hate_speech`.
4. **Questions seeking help** are `safe` — e.g., "Намайг дарамталж байна, яах вэ?" is `safe` (seeking help about harassment).
5. **Self-harm** takes priority over all other labels if self-harm indicators are present.
6. **When in doubt**, label as `safe` — false positives (blocking safe content) are worse than false negatives in an educational chatbot.

## Examples per Label

### safe (0)
- "Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ?"
- "Ажлын байранд ялгаварлан гадуурхалтаас хэрхэн хамгаалах вэ?"

### hate_speech (1)
- "Эмэгтэйчүүд удирдах албан тушаал хашихад тохиромжгүй"
- "Хөгжлийн бэрхшээлтэй хүмүүс ажиллах чадваргүй"

### harassment (2)
- "Чи юу ч мэдэхгүй тэнэг юм"
- "Чамайг хичээлд оролцуулахгүй"

### discrimination (3)
- "Эрэгтэй хүн илүү цалин авах ёстой"
- "Хөдөөнөөс ирсэн хүнийг ажилд авах хэрэггүй"

### self_harm (4)
- "Би амьдрахыг хүсэхгүй байна"
- "Би өөрийгөө гэмтээмээр байна"
