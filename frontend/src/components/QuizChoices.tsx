import { Box, Checkbox, FormControlLabel, FormGroup, Radio, RadioGroup, Theme } from '@mui/material';
import { Cancel, CheckCircleOutline } from '@mui/icons-material';
import ChoiceLabelText from './ChoiceLabelText';
import { choiceLabel } from '../utils/choiceLabel';
import { Choice } from '../types/quiz';

type Props = {
  problemType: 'single_choice' | 'multiple_choice';
  choices: Choice[];
  selectedChoices: string[];
  onSelect: (choiceId: string) => void;
  /** 答えた後か（答えた後は選び直せない） */
  showResult: boolean;
  /** 正解の選択肢の id（答えた後に API が返す） */
  correctChoiceIds: string[];
};

// 選んだ誤答の赤。ダークモードのカードの背景では error.main の明るさの比が 4.5:1 に届かないので、
// 同じ赤の明るい版にする（docs/runbooks/ux-rules.md §6）
const wrongColor = (theme: Theme) =>
  theme.palette.mode === 'dark' ? theme.palette.error.light : theme.palette.error.main;

/**
 * クイズの選択肢（I645）。記号（ア・イ・ウ・エ…）を本文と分けて出し、
 * 答えた後は正解に緑のチェック、選んだ誤答に赤い×を付ける
 */
function QuizChoices({ problemType, choices, selectedChoices, onSelect, showResult, correctChoiceIds }: Props) {
  // 1 つの選択肢の行。部品（Radio か Checkbox）だけを受け取り、記号・印・色・名前は同じに組み立てる
  const renderRow = (choice: Choice, index: number, control: React.ReactElement) => {
    const isCorrect = showResult && correctChoiceIds.includes(choice.id);
    const isSelectedWrong = showResult && !isCorrect && selectedChoices.includes(choice.id);
    const resultColor = isCorrect ? 'success.main' : isSelectedWrong ? wrongColor : undefined;
    return (
      <Box key={choice.id} mb={1} data-testid="choice-option">
        <FormControlLabel
          value={choice.id}
          control={control}
          disabled={showResult}
          label={
            // 答えた後は disabled になり、MUI の灰色がラベルの要素に付く（子へは受け継ぎで伝わるだけ）。
            // 色をこの自前の要素に直接書けば、灰色に負けない。色が無い選択肢は undefined で灰色のまま
            <Box display="flex" alignItems="center" gap={1} sx={{ color: resultColor, fontWeight: isCorrect ? 600 : 400 }}>
              <ChoiceLabelText index={index} text={choice.text} />
              {isCorrect && <CheckCircleOutline sx={{ color: 'success.main', fontSize: 20 }} />}
              {isSelectedWrong && <Cancel sx={{ color: wrongColor, fontSize: 20 }} />}
            </Box>
          }
          sx={{ width: '100%' }}
        />
      </Box>
    );
  };
  const inputProps = (choice: Choice, index: number) => ({ 'aria-label': `${choiceLabel(index)} ${choice.text}` });

  if (problemType === 'single_choice') {
    // ラジオの値は文字になるが、API は id を数字で返す。元の id で選び、選んだかの比べ方と送る id の型を API にそろえる
    const handleRadioChange = (value: string) => {
      const picked = choices.find((choice) => String(choice.id) === value);
      if (picked) onSelect(picked.id);
    };
    return (
      <RadioGroup value={selectedChoices[0] ?? ''} onChange={(e) => handleRadioChange(e.target.value)}>
        {choices.map((choice, index) => renderRow(choice, index, <Radio inputProps={inputProps(choice, index)} />))}
      </RadioGroup>
    );
  }

  return (
    <FormGroup>
      {choices.map((choice, index) =>
        renderRow(
          choice,
          index,
          <Checkbox
            checked={selectedChoices.includes(choice.id)}
            onChange={() => onSelect(choice.id)}
            inputProps={inputProps(choice, index)}
          />
        )
      )}
    </FormGroup>
  );
}

export default QuizChoices;
