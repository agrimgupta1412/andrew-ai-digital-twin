# Evaluation Plan

This is how I would test whether AndrewAI is working properly.

## 1. Persona And Teaching Style

Ask beginner ML questions and check if the answer:

- Starts with intuition.
- Uses simple examples.
- Explains step by step.
- Avoids unnecessary jargon.
- Connects the idea to a real ML project.
- Clearly avoids saying it is the real Andrew Ng.

Example question:

```text
Explain gradient descent like I am new to ML.
```

## 2. Technical Accuracy

Ask common ML questions and compare the answers with reliable ML references or retrieved notes.

Good test topics:

- Gradient descent
- Bias and variance
- Regularization
- Neural networks
- Adam optimizer
- Data-centric AI
- Model evaluation

## 3. RAG Grounding

Ask questions that should match the indexed documents. Then check the "Retrieved sources" section.

The answer should use relevant source chunks when they are available. If the retrieved context is weak, the chatbot should not pretend that it has strong evidence.

## 4. Memory Quality

Test useful memory statements such as:

```text
I am new to machine learning.
I prefer examples before equations.
I am building an image classification project.
```

Then open the Memory Dashboard and check whether these memories are visible.

Also test trivial messages like:

```text
hello
okay
thanks
```

These should not be saved as important long-term memories.

## 5. Multi-Turn Chat

Test follow-up questions in the same session.

Example:

```text
Explain logistic regression using a spam email example.
Now explain regularization using the same example.
```

The second answer should understand that "same example" means the spam email example from the previous message.

## 6. Timeline Awareness

Ask time-based questions and check whether timeline context appears.

Example:

```text
What would Andrew Ng have said about ChatGPT in 2012?
```

The answer should not claim that ChatGPT existed in 2012.

## 7. User Experience

Test the basic app controls:

- Empty input
- Missing or invalid API key
- API quota exceeded
- No indexed documents
- Reset chat
- Clear memory
- Source display
- Memory Dashboard
- Timeline page

This checks that the project does not crash during common demo situations.
