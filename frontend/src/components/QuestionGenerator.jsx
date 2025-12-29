import React, { useState } from 'react';
import axios from 'axios';
import ReviewQuestions from './ReviewQuestions'; // Import the new component
import FirebaseQuestionReview from './FirebaseQuestionReview'; // Import Firebase review component
import { useEffect } from 'react';
import { loadCachedQuestions, saveCachedQuestions } from '../utils/localStorage';
const CACHE_KEY="cached_questions"



const QuestionGenerator = () => {
  const [difficulties, setDifficulties] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [numQuestions, setNumQuestions] = useState(1);
  const [reviewMode, setReviewMode] = useState(false);
  const [firebaseReviewMode, setFirebaseReviewMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedSection, setSelectedSection] = useState("");
  const [selectedSkills, setSelectedSkills] = useState({});
  const reloadQuestionsFromBackend = async () => {
    try {
      const response = await axios.get('http://localhost:8000/load-pending-questions');
      if (response.data && response.data.questions) {
        setQuestions(response.data.questions);
        saveCachedQuestions(response.data.questions);
      }
    } catch (error) {
      console.error('Failed to reload questions from backend:', error);
    }
  };
  const questionDomains = {
   "reading_and_writing": {
      "craft_and_structure": ["words_in_context", "text_structure_and_purpose", "cross_text_connections"],
      "information_and_ideas": ["central_ideas_and_details", "command_of_evidence", "inferences"],
      "standard_english_conventions": ["boundaries", "form_structure_and_sense"],
      "expression_of_ideas": ["rhetorical_synthesis", "transitions"],
    },
    "math": { // UPDATED MATH CONTENT DOMAINS
      "algebra": [
        "linear_equations_in_one_variable",
        "linear_equations_in_two_variables",
        "linear_functions",
        "systems_of_two_linear_equations_in_two_variables",
        "linear_inequalities_in_one_or_two_variables"
      ],
      "advanced_math": [
        "equivalent_expressions",
        "nonlinear_equations_in_one_variable_and_systems_of_equations_in_two_variables",
        "nonlinear_functions"
      ],
      "problem_solving_and_data_analysis": [
        "ratios_rates_proportional_relationships_and_units",
        "percentages",
        "one_variable_data_distributions_and_measures_of_center_and_spread",
        "two_variable_data_models_and_scatterplots",
        "probability_and_conditional_probability",
        "inference_from_sample_statistics_and_margin_of_error",
        "evaluating_statistical_claims_observational_studies_and_experiments"
      ],
      "geometry_and_trigonometry": [
        "area_and_volume",
        "lines_angles_and_triangles",
        "right_triangles_and_trigonometry",
        "circles"
      ]
    }
  };

  const difficultyOptions = ["easy", "medium", "hard"];

  useEffect(() => {
    const cached = loadCachedQuestions();
    setQuestions(cached);
    console.log("Loaded questions from cache:", cached.length);
  }, []);
  
  // --- EFFECT FOR SAVING TO LOCALSTORAGE WHEN QUESTIONS CHANGE ---
  useEffect(() => {
    saveCachedQuestions(questions);
    console.log(questions.length > 0 ? "Questions cached" : "Cache cleared");
  }, [questions]);
  
  const handleLoadPendingQuestions = async () => {
    setLoading(true); // Indicate loading
    try {
      const response = await axios.get('http://localhost:8000/load-pending-questions');
      if (response.data && response.data.questions) {
        // Merge with existing questions (if any) or replace
        // For redundancy, you probably want to MERGE to combine browser cache with backend cache
        const backendQuestions = response.data.questions;
        const currentQuestions = new Set(questions.map(q => q.id)); // Assuming questions have unique 'id'
        const mergedQuestions = [...questions];

        backendQuestions.forEach(q => {
            if (!currentQuestions.has(q.id)) {
                mergedQuestions.push(q);
            }
        });

        setQuestions(mergedQuestions);
        alert(`Successfully loaded ${backendQuestions.length} questions from backend cache.`);
        console.log("Questions loaded from backend pending file:", backendQuestions.length);
      } else {
        alert("No questions found in backend pending file.");
      }
    } catch (error) {
      console.error('Error loading pending questions from backend:', error);
      alert('Error loading pending questions from backend. Please ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  };


  const toggleDifficulty = (difficulty) => {
    setDifficulties(prevDifficulties => {
      if (prevDifficulties.includes(difficulty)) {
        // Remove difficulty if already selected
        return prevDifficulties.filter(d => d !== difficulty);
      } else {
        // Add difficulty if not selected
        return [...prevDifficulties, difficulty];
      }
    });
  };

  const toggleSkill = (domain, skill) => {
    setSelectedSkills(prevSkills => {
      const domainSkills = prevSkills[domain] || [];
      if (domainSkills.includes(skill)) {
        // Remove the skill
        return {
          ...prevSkills,
          [domain]: domainSkills.filter(s => s !== skill)
        };
      } else {
        // Add the skill
        return {
          ...prevSkills,
          [domain]: [...domainSkills, skill]
        };
      }
    });
  };

  const selectAllInDomain = (domain) => {
    setSelectedSkills(prevSkills => {
      // Get the skills for the specific domain within the CURRENTLY selected section
      const allSkillsForThisDomain = questionDomains[selectedSection]?.[domain] || []; // IMPORTANT CHANGE
      return {
        ...prevSkills,
        [domain]: allSkillsForThisDomain // Set all skills for this domain
      };
    });
};
  const handleGenerateQuestions = async () => {
    setLoading(true);
    const selectedDomains = Object.keys(selectedSkills);
    const selectedSkillCategories = selectedDomains.flatMap(domain => selectedSkills[domain] || []);

    try {
      const response = await axios.post('http://localhost:8000/generate-questions', {
        section: selectedSection,
        domains: selectedDomains,
        skill_categories: selectedSkillCategories,
        difficulties,
        num_questions: numQuestions,
      });

      setQuestions((prevQuestions) => [...prevQuestions, ...response.data.questions]);
    } catch (error) {
      console.error('Error generating questions:', error);
    } finally {
      setLoading(false);
    }
  };

  const sendQuestionsToFirebase = async () => {
    try {
      console.log(questions);
      const response = await axios.post('http://localhost:8000/send-questions', {
        questions,
      });
      console.log('Questions sent to Firebase:', response.data);
      setQuestions([]);
      setReviewMode(false);
    } catch (error) {
      console.error('Error sending questions to Firebase:', error);
    }
  };
  useEffect(() => {
    const handleBeforeUnload = (event) => {
      if (questions.length > 0) {
        event.preventDefault();
        event.returnValue = "You have unsaved questions. Are you sure you want to leave?";
        return "You have unsaved questions. Are you sure you want to leave?";
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [questions]);
  return (
    <div>
      <h1>Generate SAT Questions</h1>
      <div className="section-tabs">
        {Object.keys(questionDomains).map(sectionKey => (
          <button
            key={sectionKey}
            className={`tab-button ${selectedSection === sectionKey ? 'active' : ''}`}
            onClick={() => {
                setSelectedSection(sectionKey);
                setSelectedSkills({}); // Clear selected skills when changing section
                setDifficulties([]); // Clear selected difficulties too, as they might be section-specific
            }}
          >
            {sectionKey.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())} {/* Format for display */}
          </button>
        ))}
      </div>
      <button
            type="button"
            onClick={handleLoadPendingQuestions}
            disabled={loading}
            style={{ marginLeft: '10px' }} // Add some styling
          >
            Load from Backend Cache
          </button>
      {!reviewMode && !firebaseReviewMode ? (
        <form onSubmit={(e) => e.preventDefault()}>
          {/* Domain and Skills Selection */}
          {Object.entries(questionDomains[selectedSection] || {}).map(([domain, skills]) => (
            <div key={domain} className="domain-section">
              <h3>{domain}</h3>
              <button onClick={() => selectAllInDomain(domain)}>Select All</button>
              {skills.map(skill => (
                <label key={skill}>
                  <input
                    type="checkbox"
                    checked={selectedSkills[domain]?.includes(skill) || false}
                    onChange={() => toggleSkill(domain, skill)}
                  />
                  {skill}
                  </label>
              ))}
            </div>
          ))}
          <div>
            <label>Difficulties:</label>
            <div className="difficulty-checkboxes"> {/* Optional: for styling */}
              {difficultyOptions.map((difficulty) => (
                <label key={difficulty}>
                  <input
                    type="checkbox"
                    value={difficulty}
                    checked={difficulties.includes(difficulty)}
                    onChange={() => toggleDifficulty(difficulty)}
                  />
                  {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)} {/* Capitalize for display */}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label>Number of Questions per Skill Category:</label>
            <input type="number" value={numQuestions} onChange={(e) => setNumQuestions(Number(e.target.value))} min="1" />
          </div>
          <button onClick={handleGenerateQuestions} disabled={loading}>Generate Questions</button>
          <button onClick={() => setReviewMode(true)} disabled={questions.length === 0 || loading}>
            Review Pending Questions
          </button>
          <button onClick={() => setFirebaseReviewMode(true)} disabled={loading}>
            Review Firebase Questions
          </button>
        </form>
      ) : reviewMode ? (
        <ReviewQuestions
          questions={questions}
          setQuestions={setQuestions}
          onSendToFirebase={sendQuestionsToFirebase}
          onBackToGeneration={() => setReviewMode(false)}
          onRefresh={reloadQuestionsFromBackend}
        />
      ) : firebaseReviewMode ? (
        <FirebaseQuestionReview
          onBackToGeneration={() => setFirebaseReviewMode(false)}
        />
      ) : null}
    </div>
  );
};

export default QuestionGenerator;
