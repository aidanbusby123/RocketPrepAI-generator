import React, { useState } from 'react';
import axios from 'axios';
import ReviewQuestions from './ReviewQuestions'; // Import the new component


const QuestionGenerator = () => {
  const [domains, setDomains] = useState([]);
  const [skillCategories, setSkillCategories] = useState([]);
  const [difficulties, setDifficulties] = useState([]);
  const [questions, setQuestions] = useState([]); // Store all generated questions
  const [numQuestions, setNumQuestions] = useState(1);
  const [reviewMode, setReviewMode] = useState(false); // Toggle review mode

  const domainOptions = ["craft_and_structure", "information_and_ideas", "standard_english_conventions", "expression_of_ideas"];
  const skillCategoryOptions = {
    craft_and_structure: ["words_in_context", "text_structure_and_purpose", "cross_text_connections"],
    information_and_ideas: ["central_ideas_and_details", "command_of_evidence", "inferences"],
    standard_english_conventions: ["boundaries", "form_structure_and_sense"],
    expression_of_ideas: ["rhetorical_synthesis", "transitions"],
  };
  const difficultyOptions = ["easy", "medium", "hard"];

  const handleGenerateQuestions = async () => {
    try {
      const response = await axios.post('http://localhost:8001/generate-questions', {
        domains,
        skill_categories: skillCategories,
        difficulties,
        num_questions: numQuestions,
      });

      // Append all questions from the response to the state
      setQuestions((prevQuestions) => [...prevQuestions, ...response.data.questions]);
    } catch (error) {
      console.error('Error generating questions:', error);
    }
  };

  const sendQuestionsToFirebase = async () => {
    try {
        console.log(questions);
      const response = await axios.post('http://localhost:8001/send-questions', {
        questions
      });
      console.log('Questions sent to Firebase:', response.data);
      setQuestions([]); // Clear questions after sending
      setReviewMode(false); // Exit review mode
    } catch (error) {
      console.error('Error sending questions to Firebase:', error);
    }
  };

  return (
    <div>
      <h1>Generate SAT Questions</h1>
      {!reviewMode ? (
        <form onSubmit={(e) => e.preventDefault()}>
          <div>
            <label>Domains:</label>
            <select multiple value={domains} onChange={(e) => setDomains([...e.target.selectedOptions].map(o => o.value))}>
              {domainOptions.map((domain) => (
                <option key={domain} value={domain}>{domain}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Skill Categories:</label>
            <select multiple value={skillCategories} onChange={(e) => setSkillCategories([...e.target.selectedOptions].map(o => o.value))}>
              {domains.flatMap((domain) => skillCategoryOptions[domain] || []).map((skill) => (
                <option key={skill} value={skill}>{skill}</option>
              ))}
            </select>
          </div>
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
          <button onClick={handleGenerateQuestions}>Generate Questions</button>
          <button onClick={() => setReviewMode(true)} disabled={questions.length === 0}>
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