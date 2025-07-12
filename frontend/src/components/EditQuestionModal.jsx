// src/components/EditQuestionModal.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './EditQuestionModal.css'; // Create this CSS file

const EditQuestionModal = ({ isOpen, question, setQuestions, onClose, onEditComplete }) => {
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState('');

  // Reset form when modal opens or question changes
  useEffect(() => {
    if (isOpen) {
      setNotes('');
      setMessage('');
    }
  }, [isOpen, question]);

  // If modal is not open, don't render anything
  if (!isOpen) return null;

  // Basic validation if question data is missing (shouldn't happen if called correctly)


  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!notes.trim()) {
      setMessage('Please enter notes for revision.');
      return;
    }

    setIsSubmitting(true);
    setMessage('');

    try {
      const response = await axios.post('http://localhost:8000/human-feedback', {
        index: question, // Send the full original question object
        content: notes,     // Send the revision notes
      });

      setQuestions(response.data)

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

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Revise Question</h2>
        <div className="question-preview">
          <h3>Original Question:</h3>
          <p>{question.question}</p>
          <p>Difficulty: {question.difficulty}</p>
          <p>Skill: {question.skill_category}</p>
          {/* You can display more question details here if helpful */}
        </div>

        <form onSubmit={handleSubmit} className="revision-form">
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
        <button className="modal-close-button" onClick={() => onClose()}>
          Cancel
        </button>
      </div>
    </div>
  );
};

export default EditQuestionModal;