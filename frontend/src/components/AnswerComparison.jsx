function HighlightedAnswer({ answer, phrase }) {
  if (!phrase) return answer;
  const start = answer.toLocaleLowerCase().indexOf(phrase.toLocaleLowerCase());
  if (start < 0) return answer;
  return (
    <>
      {answer.slice(0, start)}
      <mark>{answer.slice(start, start + phrase.length)}</mark>
      {answer.slice(start + phrase.length)}
    </>
  );
}

export default function AnswerComparison({ response }) {
  return (
    <div className="answer-comparison">
      <section className="answer-box student-answer">
        <h3>Student answer</h3>
        <p>
          {response ? (
            <HighlightedAnswer
              answer={response.answer}
              phrase={response.misconception_phrase}
            />
          ) : (
            <span className="answer-placeholder">
              Select a response from Analysis.
            </span>
          )}
        </p>
      </section>
      <section className="answer-box expected-answer">
        <h3>Expected answer</h3>
        <p>
          {response?.expected_answer || (
            <span className="answer-placeholder">
              No expected answer provided.
            </span>
          )}
        </p>
      </section>
    </div>
  );
}
