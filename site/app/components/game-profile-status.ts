type Pair = readonly [string, string];
export const gameProfileStatus = (status: string): Pair => status === 'observer_pilot'
    ? ['Observer pilot · Calibration pending', 'Пилот наблюдения · Калибровка ожидается']
    : status === 'adapter_foundation'
      ? ['Adapter foundation · Environment unverified', 'Основа адаптера · Среда не проверена']
      : status === 'research_only'
        ? ['Research only · Environment unverified', 'Только исследование · Среда не проверена']
        : ['Implementation status unavailable', 'Статус реализации недоступен'];
