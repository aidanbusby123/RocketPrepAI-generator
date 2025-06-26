import React, { useState } from 'react';
import axios from 'axios';
import ReviewQuestions from './ReviewQuestions'; // Import the new component

const QuestionGenerator = () => {
  const [difficulties, setDifficulties] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [numQuestions, setNumQuestions] = useState(1);
  const [reviewMode, setReviewMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedSkills, setSelectedSkills] = useState({});

  const questionDomains = {
    "craft_and_structure": ["words_in_context", "text_structure_and_purpose", "cross_text_connections"],
    "information_and_ideas": ["central_ideas_and_details", "command_of_evidence", "inferences"],
    "standard_english_conventions": ["boundaries", "form_structure_and_sense"],
    "expression_of_ideas": ["rhetorical_synthesis", "transitions"],
  };

  const difficultyOptions = ["easy", "medium", "hard"];

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
    setSelectedSkills(prevSkills => ({
      ...prevSkills,
      [domain]: questionDomains[domain]
    }));
  };

  const handleGenerateQuestions = async () => {
    setLoading(true);
    const selectedDomains = Object.keys(selectedSkills);
    const selectedSkillCategories = selectedDomains.flatMap(domain => selectedSkills[domain] || []);

    try {
      const response = await axios.post('http://localhost:8000/generate-questions', {
        section: "reading_and_writing",
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

  return (
    <div>
      <h1>Generate SAT Questions</h1>
      {!reviewMode ? (
        <form onSubmit={(e) => e.preventDefault()}>
          {/* Domain and Skills Selection */}
          {Object.entries(questionDomains).map(([domain, skills]) => (
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
            <select multiple value={difficulties} onChange={(e) => setDifficulties([...e.target.selectedOptions].map(o => o.value))}>
              {difficultyOptions.map((difficulty) => (
                <option key={difficulty} value={difficulty}>{difficulty}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Number of Questions per Skill Category:</label>
            <input type="number" value={numQuestions} onChange={(e) => setNumQuestions(Number(e.target.value))} min="1" />
          </div>
          <button onClick={handleGenerateQuestions} disabled={loading}>Generate Questions</button>
          <button onClick={() => setReviewMode(true)} disabled={questions.length === 0 || loading}>
            Review Questions
          </button>
        </form>
      ) : (
        <ReviewQuestions
          questions={questions}
          onSendToFirebase={sendQuestionsToFirebase}
          onBackToGeneration={() => setReviewMode(false)}
        />
      )}
    </div>
  );
};

export default QuestionGenerator;