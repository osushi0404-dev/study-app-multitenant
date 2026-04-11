import React, { useState, useEffect } from 'react';
import { FormControl, InputLabel, Select, MenuItem, SelectChangeEvent } from '@mui/material';
import { toast } from 'react-hot-toast';
import SubjectService from '../services/subjectService';
import { Subject } from '../services/types';

interface SubjectSelectorProps {
  value: string;
  onChange: (subjectId: string) => void;
  label?: string;
  includeAll?: boolean;
  fullWidth?: boolean;
}

export const SubjectSelector: React.FC<SubjectSelectorProps> = ({
  value,
  onChange,
  label = '科目',
  includeAll = true,
  fullWidth = true
}) => {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUserSubjects();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // フォーカス時にデータを再取得（科目が変更された可能性があるため）
  useEffect(() => {
    const handleFocus = () => {
      loadUserSubjects();
    };

    window.addEventListener('focus', handleFocus);
    return () => {
      window.removeEventListener('focus', handleFocus);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadUserSubjects = async () => {
    try {
      const subjectData = await SubjectService.getUserSubjects();
      setSubjects(subjectData);

      // デフォルトで「all」を選択（valueが空の場合）
      if (!value && includeAll) {
        onChange('all');
      } else if (!value && subjectData.length > 0) {
        onChange(String(subjectData[0].id));
      }
    } catch (error) {
      console.error('Error loading subjects:', error);
      toast.error('科目の読み込みに失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value);
  };

  return (
    <FormControl fullWidth={fullWidth} disabled={loading}>
      <InputLabel>{label}</InputLabel>
      <Select
        value={value}
        label={label}
        onChange={handleChange}
        onOpen={() => loadUserSubjects()}
      >
        {includeAll && <MenuItem value="all">すべて</MenuItem>}
        {subjects.map((subject) => (
          <MenuItem key={subject.id} value={String(subject.id)}>
            {subject.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default SubjectSelector;
