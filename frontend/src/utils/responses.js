export function parseCSV(text) {
  const rows = [];
  let row = [],
    cell = "",
    quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') {
        cell += '"';
        i++;
      } else quoted = !quoted;
    } else if (ch === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      if (row.some((value) => value.trim())) rows.push(row);
      row = [];
      cell = "";
    } else cell += ch;
  }
  if (quoted)
    throw Error("A quoted field is not closed. Please check your CSV.");
  row.push(cell);
  if (row.some((value) => value.trim())) rows.push(row);
  return rows;
}

export function validateRows(input) {
  if (!Array.isArray(input) || input.length < 3)
    throw Error("Please include at least 3 student responses.");
  if (input.length > 10000)
    throw Error("Use 10,000 responses or fewer per assessment.");
  return input.map((record, index) => {
    if (!record || typeof record !== "object" || Array.isArray(record))
      throw Error(`Row ${index + 1} must be an object.`);
    const row = {};
    for (const field of ["student_id", "question_id", "answer"]) {
      const value = record[field];
      if (
        (typeof value !== "string" && typeof value !== "number") ||
        !String(value).trim() ||
        (typeof value === "number" && !Number.isFinite(value))
      ) {
        throw Error(
          `Row ${index + 1} needs valid student_id, question_id, and answer values.`,
        );
      }
      row[field] = String(value).trim();
    }
    for (const field of [
      "question",
      "expected_answer",
      "misconception",
      "misconception_phrase",
      "explanation",
    ]) {
      if (record[field] === undefined || record[field] === "") continue;
      if (typeof record[field] !== "string")
        throw Error(`Row ${index + 1}: ${field} must be text.`);
      row[field] = record[field].trim();
    }
    for (const [scoreField, maxField] of [
      ["score", "max_score"],
      ["follow_up_score", "follow_up_max_score"],
    ]) {
      const rawScore = record[scoreField];
      if (rawScore === undefined || rawScore === "") continue;
      const rawMax = record[maxField];
      const score = Number(rawScore),
        maxScore = Number(rawMax);
      if (
        ![rawScore, rawMax].every(
          (value) =>
            (typeof value === "string" && value.trim() !== "") ||
            typeof value === "number",
        ) ||
        !Number.isFinite(score) ||
        !Number.isFinite(maxScore) ||
        maxScore <= 0 ||
        score < 0 ||
        score > maxScore
      ) {
        throw Error(
          `Row ${index + 1} has an invalid ${scoreField} or ${maxField}.`,
        );
      }
      row[scoreField] = score;
      row[maxField] = maxScore;
    }
    return row;
  });
}

export async function readResponseFile(file) {
  if (file.size > 2 * 1024 * 1024)
    throw Error("Please use a file smaller than 2 MB.");
  const text = (await file.text()).replace(/^\uFEFF/, "");
  if (file.name.toLowerCase().endsWith(".json"))
    return validateRows(JSON.parse(text));
  if (!file.name.toLowerCase().endsWith(".csv"))
    throw Error("Choose a CSV or JSON file.");
  const csv = parseCSV(text);
  const headers = csv.shift()?.map((value) => value.trim());
  if (!headers) throw Error("The file is empty.");
  if (
    !["student_id", "question_id", "answer"].every((field) =>
      headers.includes(field),
    )
  )
    throw Error(
      "CSV headers must include student_id, question_id, and answer.",
    );
  if (new Set(headers).size !== headers.length)
    throw Error("Each CSV column header must be unique.");
  const rows = csv.map((cells, index) => {
    if (cells.length !== headers.length)
      throw Error(`CSV row ${index + 2} has a different number of columns.`);
    return Object.fromEntries(headers.map((header, i) => [header, cells[i]]));
  });
  return validateRows(rows);
}

export function summarizeResponses(responses) {
  const scored = responses.filter((row) => row.score !== undefined);
  const paired = scored.filter((row) => row.follow_up_score !== undefined);
  function percentage(rows, scoreField, maxField) {
    const total = rows.reduce((sum, row) => sum + row[maxField], 0);
    return total
      ? (rows.reduce((sum, row) => sum + row[scoreField], 0) / total) * 100
      : null;
  }
  const students = new Map();
  for (const row of responses) {
    const current = students.get(row.student_id) || {
      student: row.student_id,
      score: 0,
      total: 0,
      followUp: 0,
      followUpTotal: 0,
      baselineCount: 0,
      followUpCount: 0,
      pairedCount: 0,
      responseCount: 0,
    };
    current.responseCount++;
    if (row.score !== undefined) {
      current.score += row.score;
      current.total += row.max_score;
      current.baselineCount++;
    }
    if (row.follow_up_score !== undefined) {
      current.followUp += row.follow_up_score;
      current.followUpTotal += row.follow_up_max_score;
      current.followUpCount++;
    }
    if (row.score !== undefined && row.follow_up_score !== undefined)
      current.pairedCount++;
    students.set(row.student_id, current);
  }
  const before = percentage(paired, "score", "max_score"),
    after = percentage(paired, "follow_up_score", "follow_up_max_score");
  return {
    students: students.size,
    questions: new Set(responses.map((row) => row.question_id)).size,
    scored: scored.length,
    baseline: percentage(scored, "score", "max_score"),
    before,
    after,
    change: before === null || after === null ? null : after - before,
    paired: paired.length,
    matchedStudents: new Set(paired.map((row) => row.student_id)).size,
    missingFollowUp: responses.filter(
      (row) => row.follow_up_score === undefined,
    ).length,
    missingBaseline: responses.length - scored.length,
    studentScores: [...students.values()],
  };
}
