import { expect, it } from 'vitest';
import { gameProfileStatus } from './game-profile-status';

it.each(['verified', 'unknown', '', 'research_only_typo'])('does not invent research or verified support for an unrecognized state: %s', status => {
  expect(gameProfileStatus(status)).toEqual(['Implementation status unavailable', 'Статус реализации недоступен']);
});

it('preserves explicit evidence limits of all current catalog states', () => {
  expect(gameProfileStatus('research_only')).toEqual(['Research only · Environment unverified', 'Только исследование · Среда не проверена']);
  expect(gameProfileStatus('adapter_foundation')).toEqual(['Adapter foundation · Environment unverified', 'Основа адаптера · Среда не проверена']);
  expect(gameProfileStatus('observer_pilot')).toEqual(['Observer pilot · Calibration pending', 'Пилот наблюдения · Калибровка ожидается']);
});
