import React, { useState, useMemo } from 'react';
import axios from 'axios';
import ConfirmDeleteModal from '../components/ConfirmDeleteModal';
import EditQuestionModal from '../components/EditQuestionModal';
import './ReviewQuestions.css';

const ReviewQuestions = ({
  questions,
  setQuestions,
  onSendToFirebase,
  onBackToGeneration,
  onRefresh,
  onQuestionDeleted,
  skillDisplayNameMap,
  sectionDisplayNameMap,
  onQuestionUpdated
}) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [questionToDelete, setQuestionToDelete] = useState(null);
  const [questionToDeleteIndex, setQuestionToDeleteIndex] = useState(null);
  const [deleteMessage, setDeleteMessage] = useState('');

  const [showEditModal, setShowEditModal] = useState(false);
  const [questionToEdit, setQuestionToEdit] = useState(null);
  const [questionToEditIndex, setQuestionToEditIndex] = useState(null);

  const handleOpenEditModal = (index) => {
    const question = questions[index];
    if (question) {
      setQuestionToEdit(question);
      setQuestionToEditIndex(index);
      setShowEditModal(true);
    }
  };

  const handleEditComplete = async () => {
    setShowEditModal(false);
    setQuestionToEdit(null);
    setQuestionToEditIndex(null);
    if (onRefresh) {
      await onRefresh();
    }
  };

  const initiateDelete = (index) => {
    const question = questions[index];
    if (question) {
      setQuestionToDelete(question);
      setQuestionToDeleteIndex(index);
      setShowDeleteConfirm(true);
      setDeleteMessage('');
    }
  };

  const handleDeleteConfirmed = async () => {
    if (questionToDeleteIndex == null) return;

    setShowDeleteConfirm(false);
    setDeleteMessage('Deleting question...');

    try {
      const response = await axios.post('http://localhost:8000/remove-question', {
        index: questionToDeleteIndex,
      });

      if (onRefresh) {
        await onRefresh();
      }

      setDeleteMessage('Question deleted successfully!');
      console.log('Question deleted:', response.data);

      if (onQuestionDeleted) {
        onQuestionDeleted(questionToDelete);
      }

      setQuestionToDelete(null);
      setQuestionToDeleteIndex(null);
    } catch (error) {
      const msg = error.response?.data?.detail || error.message;
      setDeleteMessage(`Error deleting question: ${msg}`);
      console.error('Error deleting question:', msg);
      setQuestionToDelete(null);
      setQuestionToDeleteIndex(null);
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false);
    setQuestionToDelete(null);
    setQuestionToDeleteIndex(null);
    setDeleteMessage('');
  };

  const tableRows = useMemo(() => {
    if (!questions || questions.length === 0) {
      return (
        <tr>
          <td colSpan="8" style={{ textAlign: 'center', padding: '20px' }}>
            No questions available for review. Generate some questions!
          </td>
        </tr>
      );
    }
    return questions.map((question, index) => (
      <tr key={index}>
        <td>{index + 1}</td>
        <td>{question.section}</td>
        <td>{question.domain}</td>
        <td>{question.skill_category}</td>
        <td>{question.difficulty}</td>

        <td>
          {/* Conditional rendering for the question graphic */}
          {question.graphic_url ? (
            <div className="question-content">
              <img src={question.graphic_url} alt="Question Diagram" className="question-graphic" />
              <p>{question.question}</p>
            </div>
          ) : (
            <p>{question.question}</p>
          )}
        </td>
        <td>{question.choices.join(', ')}</td>
        <td>
          <button
            className="edit-button"
            onClick={() => handleOpenEditModal(index)}
          >
            Edit
          </button>
          <button
            className="delete-button"
            onClick={() => initiateDelete(index)}
          >
            Delete
          </button>
        </td>
      </tr>
    ));
  }, [questions, skillDisplayNameMap, sectionDisplayNameMap]);

  return (
    <div className="review-container">
      <h2>Review Generated Questions</h2>
      {deleteMessage && <p className="delete-status-message">{deleteMessage}</p>}
      <table className="review-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Section</th>
            <th>Domain</th>
            <th>Skill Category</th>
            <th>Difficulty</th>
            <th>Question Text</th>
            <th>Choices</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>{tableRows}</tbody>
      </table>
      <div className="review-buttons">
        <button
          className="send-button"
          onClick={onSendToFirebase}
          disabled={questions.length === 0}
        >
          Send to Firebase
        </button>
        <button
          className="back-button"
          onClick={onBackToGeneration}
        >
          Back to Generation
        </button>
      </div>

      <ConfirmDeleteModal
        isOpen={showDeleteConfirm}
        message={
          questionToDelete
            ? `Are you sure you want to delete this question: "${questionToDelete.question.slice(0, 80)}...?"`
            : ''
        }
        onConfirm={handleDeleteConfirmed}
        onCancel={handleCancelDelete}
      />

      <EditQuestionModal
        isOpen={showEditModal}
        question={questionToEditIndex}
        setQuestions={setQuestions}
        onClose={() => handleEditComplete(null)}
        onEditComplete={handleEditComplete}
      />
    </div>
  );
};

export default ReviewQuestions;
