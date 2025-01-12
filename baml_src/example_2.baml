enum Category {
    Refund
    CancelOrder
    TechnicalSupport
    AccountIssue
    Question
}

class Message {
  role string
  message string
}


function ClassifyConversation(messages: Message[]) -> Category[] {
  client GPT4
  prompt #"
    {# output_format is a helper to print out Category[] #}
    {{ ctx.output_format(prefix="Classify the following conversation into following:") }}


    {% for m in messages %}
    {{ _.chat(m.role) }}
    {{ m.message }}
    {% endfor %}

  "#
}
