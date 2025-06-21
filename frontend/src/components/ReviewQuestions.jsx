import React from 'react';
import './ReviewQuestions.css'; // Import the CSS file

const ReviewQuestions = ({ questions, onSendToFirebase, onBackToGeneration }) => {
  return (
    <div className="review-container">
      <h2>Review Generated Questions</h2>
      <table className="review-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Domain</th>
            <th>Skill Category</th>
            <th>Difficulty</th>
            <th>Question Text</th>
          </tr>
        </thead>
        <tbody>
          {questions.map((question, index) => (
            <tr key={index}>
              <td>{index + 1}</td>
              <td>{question.domain}</td>
              <td>{question.skill_category}</td>
              <td>{question.difficulty}</td>
              <td>{question.question}</td>
              <td>{question.choices}</td>
              <td>{question.correct_answer}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="review-buttons">
        <button className="send-button" onClick={onSendToFirebase}>Send to Firebase</button>
        <button className="back-button" onClick={onBackToGeneration}>Back to Generation</button>
      </div>
    </div>
  );
};

export default ReviewQuestions;