// src/components/EditQuestionModal.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './EditQuestionModal.css'; // Create this CSS file

const EditQuestionModal = ({ isOpen, question, setQuestions, onClose, onEditComplete, isFirebaseQuestion = false }) => {
  const [editedQuestion, setEditedQuestion] = useState({
    question: '',
    choices: ['', '', '', ''],
    correct_answer: '',
    difficulty: '',
    section: '',
    domain: '',
    skill_category: ''
  });
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [editMode, setEditMode] = useState('direct'); // 'direct' or 'feedback'

  // Reset form when modal opens or question changes
  useEffect(() => {
    if (isOpen && question) {
      if (isFirebaseQuestion) {
        // For Firebase questions, populate the form with current values
        setEditedQuestion({
          question: question.question || '',
          choices: question.choices || ['', '', '', ''],
          correct_answer: question.correct_answer || '',
          difficulty: question.difficulty || '',
          section: question.section || '',
          domain: question.domain || '',
          skill_category: question.skill_category || ''
        });
        setEditMode('direct');
      } else {
        // For pending questions, use feedback mode
        setEditMode('feedback');
      }
      setNotes('');
      setMessage('');
    }
  }, [isOpen, question, isFirebaseQuestion]);

  // If modal is not open, don't render anything
  if (!isOpen || !question) return null;

  const handleDirectEdit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage('');

    try {
      const updatedQuestion = {
        ...question,
        ...editedQuestion
      };

      // Call the parent's callback with the updated question
      await onEditComplete(updatedQuestion);
      setMessage('Question updated successfully!');
      
      setTimeout(() => {
        onClose();
      }, 1500);

    } catch (error) {
      setMessage(`Error updating question: ${error.message}`);
      console.error('Error updating question:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!notes.trim()) {
      setMessage('Please enter notes for revision.');
      return;
    }

    setIsSubmitting(true);
    setMessage('');

    try {
      const response = await axios.post('http://localhost:8000/human-feedback', {
        index: question, // Send the question index for pending questions
        content: notes,     // Send the revision notes
      });

      if (setQuestions) {
        setQuestions(response.data.questions);
      }

      setMessage('Question revision request sent successfully!');
      console.log('Revision Result:', response.data);

      // Call the parent's callback to update the question list and close modal
      setTimeout(() => {
        onEditComplete(response.data.revised_question); // Pass the revised question back
        onClose(); // Close the modal
      }, 1500);

    } catch (error) {
      if (error.response) {
        setMessage(`Error submitting feedback: ${error.response.data.detail || error.message}`);
        console.error('Error sending human feedback (server response):', error.response.data);
      } else {
        setMessage(`Error submitting feedback: ${error.message}`);
        console.error('Error sending human feedback (network/other):', error.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChoiceChange = (index, value) => {
    const newChoices = [...editedQuestion.choices];
    newChoices[index] = value;
    setEditedQuestion(prev => ({ ...prev, choices: newChoices }));
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>{editMode === 'direct' ? 'Edit Question' : 'Revise Question'}</h2>
        
        {editMode === 'direct' ? (
          // Direct editing form for Firebase questions
          <form onSubmit={handleDirectEdit} className="edit-form">
            <div className="form-group">
              <label htmlFor="question-text">Question Text:</label>
              <textarea
                id="question-text"
                value={editedQuestion.question}
                onChange={(e) => setEditedQuestion(prev => ({ ...prev, question: e.target.value }))}
                rows="4"
                required
              />
            </div>

            <div className="form-group">
              <label>Answer Choices:</label>
              {editedQuestion.choices.map((choice, index) => (
                <div key={index} className="choice-input">
                  <label htmlFor={`choice-${index}`}>Choice {String.fromCharCode(65 + index)}:</label>
                  <input
                    id={`choice-${index}`}
                    type="text"
                    value={choice}
                    onChange={(e) => handleChoiceChange(index, e.target.value)}
                    required
                  />
                </div>
              ))}
            </div>

            <div className="form-group">
              <label htmlFor="correct-answer">Correct Answer:</label>
              <select
                id="correct-answer"
                value={editedQuestion.correct_answer}
                onChange={(e) => setEditedQuestion(prev => ({ ...prev, correct_answer: e.target.value }))}
                required
              >
                <option value="">Select correct answer</option>
                <option value="A">A</option>
                <option value="B">B</option>
                <option value="C">C</option>
                <option value="D">D</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="difficulty">Difficulty:</label>
              <select
                id="difficulty"
                value={editedQuestion.difficulty}
                onChange={(e) => setEditedQuestion(prev => ({ ...prev, difficulty: e.target.value }))}
                required
              >
                <option value="">Select difficulty</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Updating...' : 'Update Question'}
            </button>
            {message && <p className={`form-message ${message.includes('successfully') ? 'success' : ''}`}>{message}</p>}
          </form>
        ) : (
          // Feedback form for pending questions
          <>
            <div className="question-preview">
              <h3>Original Question:</h3>
              <p>{question.question}</p>
              <p>Difficulty: {question.difficulty}</p>
              <p>Skill: {question.skill_category}</p>
            </div>

            <form onSubmit={handleFeedbackSubmit} className="revision-form">
              <label htmlFor="notes">Notes for Revision:</label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g., 'Make it harder for students, add more complex vocabulary', 'Clarify option B', 'Change the scenario'"
                rows="8"
                required
              ></textarea>
              <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Submitting...' : 'Submit Revision'}
              </button>
              {message && <p className={`form-message ${message.includes('successfully') ? 'success' : ''}`}>{message}</p>}
            </form>
          </>
        )}

        <button className="modal-close-button" onClick={() => onClose()}>
          Cancel
        </button>
      </div>
    </div>
  );
};

export default EditQuestionModal;
