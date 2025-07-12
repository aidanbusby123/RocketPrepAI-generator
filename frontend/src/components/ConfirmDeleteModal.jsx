// src/components/ConfirmDeleteModal.jsx
import React from 'react';


const ConfirmDeleteModal = ({ isOpen, message, onConfirm, onCancel }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <p>{message}</p>
        <div className="modal-actions">
          <button className="modal-button confirm" onClick={onConfirm}>Confirm</button>
          <button className="modal-button cancel" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDeleteModal;