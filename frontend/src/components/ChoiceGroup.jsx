import { useId } from "react";
import { Check } from "lucide-react";

export default function ChoiceGroup({
  label,
  options,
  value,
  onChange,
  disabled = false,
}) {
  const name = useId();
  return (
    <fieldset className="choice-field" disabled={disabled}>
      <legend>{label}</legend>
      <div className="choice-group">
        {options.map((option) => (
          <label
            className={`choice-option ${value === option ? "choice-selected" : ""}`}
            key={option}
          >
            <input
              type="radio"
              name={name}
              value={option}
              checked={value === option}
              onChange={() => onChange(option)}
            />
            <span>{option}</span>
            {value === option && <Check size={14} aria-hidden="true" />}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
