import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import ConfirmDeleteModal from './ConfirmDeleteModal';
import EditQuestionModal from './EditQuestionModal';
import './ReviewQuestions.css';

const FirebaseQuestionReview = ({
  onBackToGeneration,
  skillDisplayNameMap,
  sectionDisplayNameMap
}) => {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // Filter states
  const [selectedSection, setSelectedSection] = useState('');
  const [selectedDomain, setSelectedDomain] = useState('');
  const [selectedSkillCategory, setSelectedSkillCategory] = useState('');
  const [selectedDifficulty, setSelectedDifficulty] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Modal states
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [questionToDelete, setQuestionToDelete] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [questionToEdit, setQuestionToEdit] = useState(null);

  // Question structure matching your existing system
  const questionDomains = {
    "reading_and_writing": {
      "craft_and_structure": ["words_in_context", "text_structure_and_purpose", "cross_text_connections"],
      "information_and_ideas": ["central_ideas_and_details", "command_of_evidence", "inferences"],
      "standard_english_conventions": ["boundaries", "form_structure_and_sense"],
      "expression_of_ideas": ["rhetorical_synthesis", "transitions"],
    },
    "math": {
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

  // Load questions from Firebase
  const loadFirebaseQuestions = async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (selectedSection) params.append('section', selectedSection);
      if (selectedDomain) params.append('domain', selectedDomain);
      if (selectedSkillCategory) params.append('skill_category', selectedSkillCategory);
      if (selectedDifficulty) params.append('difficulty', selectedDifficulty);

      const response = await axios.get(`http://localhost:8000/firebase-questions?${params}`);
      setQuestions(response.data.questions || []);
    } catch (error) {
      console.error('Error loading Firebase questions:', error);
      setError('Failed to load questions from Firebase');
    } finally {
      setLoading(false);
    }
  };

  // Load questions on component mount and when filters change
  useEffect(() => {
    loadFirebaseQuestions();
  }, [selectedSection, selectedDomain, selectedSkillCategory, selectedDifficulty]);

  // Reset dependent filters when parent filter changes
  useEffect(() => {
    setSelectedDomain('');
    setSelectedSkillCategory('');
  }, [selectedSection]);

  useEffect(() => {
    setSelectedSkillCategory('');
  }, [selectedDomain]);

  // Filter questions by search term
  const filteredQuestions = useMemo(() => {
    if (!searchTerm) return questions;
    
    return questions.filter(question => 
      question.question?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      question.choices?.some(choice => choice.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  }, [questions, searchTerm]);

  // Handle edit modal
  const handleOpenEditModal = (question) => {
    setQuestionToEdit(question);
    setShowEditModal(true);
  };

  const handleEditComplete = async (updatedQuestion) => {
    if (!updatedQuestion || !questionToEdit) return;

    try {
      setMessage('Updating question...');
      
      const response = await axios.put(
        `http://localhost:8000/firebase-questions/${questionToEdit.id}`,
        { question: updatedQuestion }
      );

      setMessage('Question updated successfully!');
      await loadFirebaseQuestions(); // Reload questions
      
      setShowEditModal(false);
      setQuestionToEdit(null);
    } catch (error) {
      console.error('Error updating question:', error);
      setError('Failed to update question');
    }
  };

  // Handle delete
  const initiateDelete = (question) => {
    setQuestionToDelete(question);
    setShowDeleteConfirm(true);
  };

  const handleDeleteConfirmed = async () => {
    if (!questionToDelete) return;

    try {
      setMessage('Deleting question...');
      
      await axios.delete(
        `http://localhost:8000/firebase-questions/${questionToDelete.id}?section=${questionToDelete.section}`
      );

      setMessage('Question deleted successfully!');
      await loadFirebaseQuestions(); // Reload questions
      
      setShowDeleteConfirm(false);
      setQuestionToDelete(null);
    } catch (error) {
      console.error('Error deleting question:', error);
      setError('Failed to delete question');
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false);
    setQuestionToDelete(null);
  };

  // Get available domains for selected section
  const availableDomains = selectedSection ? Object.keys(questionDomains[selectedSection] || {}) : [];
  
  // Get available skill categories for selected domain
  const availableSkillCategories = (selectedSection && selectedDomain) 
    ? questionDomains[selectedSection][selectedDomain] || []
    : [];

  const tableRows = useMemo(() => {
    if (loading) {
      return (
        <tr>
          <td colSpan="9" style={{ textAlign: 'center', padding: '20px' }}>
            Loading questions...
          </td>
        </tr>
      );
    }

    if (filteredQuestions.length === 0) {
      return (
        <tr>
          <td colSpan="9" style={{ textAlign: 'center', padding: '20px' }}>
            No questions found matching your criteria.
          </td>
        </tr>
      );
    }

    return filteredQuestions.map((question, index) => (
      <tr key={question.id || index}>
        <td>{index + 1}</td>
        <td>{question.section}</td>
        <td>{question.domain}</td>
        <td>{question.skill_category}</td>
        <td>{question.difficulty}</td>
        <td>
          {question.graphic_url ? (
            <div className="question-content">
              <img src={question.graphic_url} alt="Question Diagram" className="question-graphic" />
              <p>{question.question}</p>
            </div>
          ) : (
            <p>{question.question}</p>
          )}
        </td>
        <td>{question.choices?.join(', ')}</td>
        <td>{question.correct_answer}</td>
        <td>
          <button
            className="edit-button"
            onClick={() => handleOpenEditModal(question)}
          >
            Edit
          </button>
          <button
            className="delete-button"
            onClick={() => initiateDelete(question)}
          >
            Delete
          </button>
        </td>
      </tr>
    ));
  }, [filteredQuestions, loading]);

  return (
    <div className="review-container">
      <h2>Review Firebase Questions</h2>
      
      {error && <p className="error-message" style={{ color: 'red' }}>{error}</p>}
      {message && <p className="status-message" style={{ color: 'green' }}>{message}</p>}

      {/* Filters */}
      <div className="filters-section" style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '5px' }}>
        <h3>Filters</h3>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '15px' }}>
          {/* Section Filter */}
          <div>
            <label>Section:</label>
            <select 
              value={selectedSection} 
              onChange={(e) => setSelectedSection(e.target.value)}
              style={{ width: '100%', padding: '5px' }}
            >
              <option value="">All Sections</option>
              {Object.keys(questionDomains).map(section => (
                <option key={section} value={section}>
                  {section.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          {/* Domain Filter */}
          <div>
            <label>Domain:</label>
            <select 
              value={selectedDomain} 
              onChange={(e) => setSelectedDomain(e.target.value)}
              disabled={!selectedSection}
              style={{ width: '100%', padding: '5px' }}
            >
              <option value="">All Domains</option>
              {availableDomains.map(domain => (
                <option key={domain} value={domain}>
                  {domain.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          {/* Skill Category Filter */}
          <div>
            <label>Skill Category:</label>
            <select 
              value={selectedSkillCategory} 
              onChange={(e) => setSelectedSkillCategory(e.target.value)}
              disabled={!selectedDomain}
              style={{ width: '100%', padding: '5px' }}
            >
              <option value="">All Skills</option>
              {availableSkillCategories.map(skill => (
                <option key={skill} value={skill}>
                  {skill.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          {/* Difficulty Filter */}
          <div>
            <label>Difficulty:</label>
            <select 
              value={selectedDifficulty} 
              onChange={(e) => setSelectedDifficulty(e.target.value)}
              style={{ width: '100%', padding: '5px' }}
            >
              <option value="">All Difficulties</option>
              {difficultyOptions.map(difficulty => (
                <option key={difficulty} value={difficulty}>
                  {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Search */}
        <div>
          <label>Search Questions:</label>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search question text or choices..."
            style={{ width: '100%', padding: '8px', marginTop: '5px' }}
          />
        </div>

        <div style={{ marginTop: '10px' }}>
          <button onClick={loadFirebaseQuestions} disabled={loading}>
            Refresh Questions
          </button>
          <span style={{ marginLeft: '15px', color: '#666' }}>
            Showing {filteredQuestions.length} questions
          </span>
        </div>
      </div>

      {/* Questions Table */}
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
            <th>Correct Answer</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>{tableRows}</tbody>
      </table>

      <div className="review-buttons">
        <button
          className="back-button"
          onClick={onBackToGeneration}
        >
          Back to Generation
        </button>
      </div>

      {/* Modals */}
      <ConfirmDeleteModal
        isOpen={showDeleteConfirm}
        message={
          questionToDelete
            ? `Are you sure you want to delete this question: "${questionToDelete.question?.slice(0, 80)}..."?`
            : ''
        }
        onConfirm={handleDeleteConfirmed}
        onCancel={handleCancelDelete}
      />

      <EditQuestionModal
        isOpen={showEditModal}
        question={questionToEdit}
        onClose={() => {
          setShowEditModal(false);
          setQuestionToEdit(null);
        }}
        onEditComplete={handleEditComplete}
        isFirebaseQuestion={true}
      />
    </div>
  );
};

export default FirebaseQuestionReview;
