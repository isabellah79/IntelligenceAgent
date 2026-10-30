/* Portable review state. No network calls, dependencies, or patient data. */
(function (root) {
  'use strict';
  const DIMENSIONS = ['evidence_strength', 'population_applicability', 'selection_justification', 'tradeoffs'];
  const VERSION = 'oncology-review-1.0';
  const copy = value => JSON.parse(JSON.stringify(value));
  const validGrade = value => Number.isInteger(value) && value >= 0 && value <= 4;
  const complete = population => DIMENSIONS.every(d => validGrade(population.scientific_grades[d]));
  const answered = population => DIMENSIONS.every(d => population.statuses[d] !== 'unrated');
  function fresh(data, id, now) {
    return {
      schema_version: VERSION, dataset_id: data.dataset_id, review_id: id,
      created_at: now, updated_at: now,
      reviewer: {name: '', specialty: '', review_date: ''},
      active_case: data.cases[0].case_id, active_populations: {}, show_ai: false,
      populations: Object.fromEntries(data.cases.flatMap(c => c.populations.map(p => [p.option_id, {
        scientific_grades: Object.fromEntries(DIMENSIONS.map(d => [d, null])),
        statuses: Object.fromEntries(DIMENSIONS.map(d => [d, 'unrated'])),
        notes: '', criteria_edits: '', evidence_notes: '', decision: '', confidence: '',
        ai_viewed_at: null, independent_snapshot: null, updated_at: now
      }]))),
      treatments: Object.fromEntries(data.cases.map(c => [c.case_id, {preferred: '', reason: ''}]))
    };
  }
  function snapshot(population, now) {
    if (!population.ai_viewed_at) {
      population.independent_snapshot = complete(population) ? {
        scientific_grades: copy(population.scientific_grades), notes: population.notes,
        criteria_edits: population.criteria_edits, evidence_notes: population.evidence_notes,
        decision: population.decision, confidence: population.confidence, recorded_at: now
      } : null;
    }
  }
  function grade(state, optionId, dimension, value, now) {
    if (!DIMENSIONS.includes(dimension) || !Object.hasOwn(state.populations, optionId)) throw new Error('Unknown population or dimension.');
    const p = state.populations[optionId];
    if (value === 'unable' || value === '') {
      p.scientific_grades[dimension] = null;
      p.statuses[dimension] = value === 'unable' ? 'unable' : 'unrated';
    } else {
      if (!validGrade(value)) throw new Error('Ratings must be integers from 0 to 4.');
      p.scientific_grades[dimension] = value;
      p.statuses[dimension] = 'scored';
    }
    p.updated_at = state.updated_at = now;
    snapshot(p, now);
  }
  function note(state, optionId, field, value, now) {
    if (!['notes', 'criteria_edits', 'evidence_notes', 'decision', 'confidence'].includes(field) || typeof value !== 'string' || value.length > 20000) throw new Error('Invalid review field.');
    const p = state.populations[optionId];
    if (!p) throw new Error('Unknown population.');
    p[field] = value;
    p.updated_at = state.updated_at = now;
    snapshot(p, now);
  }
  function reveal(state, optionId, now) {
    const p = state.populations[optionId];
    if (!p) throw new Error('Unknown population.');
    if (!p.ai_viewed_at) {
      snapshot(p, now);
      p.ai_viewed_at = now;
    }
    state.updated_at = now;
  }
  function score(population, weights) {
    if (!complete(population)) return null;
    return DIMENSIONS.reduce((sum, d) => sum + weights[d] * population.scientific_grades[d] / 4, 0) * 100;
  }
  function summary(state) {
    const values = Object.values(state.populations);
    return {total: values.length, reviewed: values.filter(answered).length,
      numeric: values.filter(complete).length,
      independent: values.filter(p => p.independent_snapshot !== null).length};
  }
  function calibration(state, data) {
    return data.cases.flatMap(c => c.populations.flatMap(p => {
      const review = state.populations[p.option_id], saved = review.independent_snapshot;
      if (!saved || !DIMENSIONS.every(d => validGrade(saved.scientific_grades[d]))) return [];
      return [{file: c.input_id, input_sha256: c.input_sha256, option_id: p.option_id, case_id: c.case_id,
        scientific_grades: copy(saved.scientific_grades), reviewer: state.reviewer.name || 'Anonymous',
        review_date: state.reviewer.review_date, specialty: state.reviewer.specialty,
        notes: saved.notes, criteria_edits: saved.criteria_edits, evidence_notes: saved.evidence_notes,
        confidence: saved.confidence, ratings_source: 'independent_before_ai',
        recorded_at: saved.recorded_at, ai_viewed_after_snapshot: Boolean(review.ai_viewed_at),
        review_id: state.review_id, dataset_id: data.dataset_id}];
    }));
  }
  function restore(raw, data) {
    const candidate = raw && raw.review ? raw.review : raw;
    if (!candidate || candidate.schema_version !== VERSION || candidate.dataset_id !== data.dataset_id) throw new Error('This review belongs to a different form or dataset.');
    if (typeof candidate.review_id !== 'string' || !candidate.review_id) throw new Error('Missing review identity.');
    const state = fresh(data, candidate.review_id, String(candidate.created_at || ''));
    for (const field of ['name', 'specialty', 'review_date']) {
      if (typeof candidate.reviewer?.[field] !== 'string' || candidate.reviewer[field].length > 1000) throw new Error('Invalid reviewer details.');
      state.reviewer[field] = candidate.reviewer[field];
    }
    if (!candidate.populations || Object.keys(candidate.populations).length !== Object.keys(state.populations).length) throw new Error('Population list does not match this form.');
    for (const [id, population] of Object.entries(candidate.populations)) {
      if (!Object.hasOwn(state.populations, id)) throw new Error('Unknown population in imported review.');
      const clean = state.populations[id];
      for (const d of DIMENSIONS) {
        const status = population.statuses?.[d], rating = population.scientific_grades?.[d];
        if (!['unrated', 'unable', 'scored'].includes(status) || (status === 'scored' ? !validGrade(rating) : rating !== null)) throw new Error('Invalid or inconsistent scientific rating.');
        clean.statuses[d] = status; clean.scientific_grades[d] = rating;
      }
      for (const field of ['notes', 'criteria_edits', 'evidence_notes', 'decision', 'confidence']) {
        if (typeof population[field] !== 'string' || population[field].length > 20000) throw new Error('Invalid feedback text.');
        clean[field] = population[field];
      }
      if (population.ai_viewed_at !== null && typeof population.ai_viewed_at !== 'string') throw new Error('Invalid AI exposure record.');
      clean.ai_viewed_at = population.ai_viewed_at;
      if (population.independent_snapshot !== null) {
        const independent = population.independent_snapshot;
        if (!independent || !DIMENSIONS.every(d => validGrade(independent.scientific_grades?.[d]))) throw new Error('Invalid independent-rating snapshot.');
        clean.independent_snapshot = copy(independent);
      }
      clean.updated_at = String(population.updated_at || candidate.updated_at || '');
    }
    for (const c of data.cases) {
      const entry = candidate.treatments?.[c.case_id];
      if (!entry || typeof entry.preferred !== 'string' || typeof entry.reason !== 'string' || entry.reason.length > 20000) throw new Error('Invalid treatment feedback.');
      if (entry.preferred && !['tie', 'uncertain', 'none', ...c.populations.map(p => p.option_id)].includes(entry.preferred)) throw new Error('Unknown preferred population.');
      state.treatments[c.case_id] = {preferred: entry.preferred, reason: entry.reason};
    }
    if (data.cases.some(c => c.case_id === candidate.active_case)) state.active_case = candidate.active_case;
    for (const c of data.cases) {
      const id = candidate.active_populations?.[c.case_id];
      if (c.populations.some(p => p.option_id === id)) state.active_populations[c.case_id] = id;
    }
    state.show_ai = candidate.show_ai === true;
    state.updated_at = String(candidate.updated_at || candidate.created_at || '');
    return state;
  }
  function scriptJSON(value) {
    return JSON.stringify(value).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
  }
  const api = {DIMENSIONS, VERSION, fresh, grade, note, reveal, score, complete, answered, summary, calibration, restore, scriptJSON};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.OncologyReviewCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
