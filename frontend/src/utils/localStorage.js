// src/utils/localStorage.js
const CACHE_KEY = "cached_questions";

export const loadCachedQuestions = () => {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    return cached ? JSON.parse(cached) : [];
  } catch (err) {
    console.error("Failed to load questions from localStorage:", err);
    localStorage.removeItem(CACHE_KEY);
    return [];
  }
};

export const saveCachedQuestions = (questions) => {
  if (questions.length > 0) {
    localStorage.setItem(CACHE_KEY, JSON.stringify(questions));
  } else {
    localStorage.removeItem(CACHE_KEY);
  }
};

export const clearCache = () => {
  localStorage.removeItem(CACHE_KEY);
};
