// Invented UI fixtures, not game mechanics, prices or a supported character build.
export const builds=[
 {id:'balanced',name:['Равновесие','Balance'],tag:['Спокойный темп','Steady pace'],focus:['Гибкость роли','Role flexibility'],tradeoff:['Без специализации на одном сценарии','No specialization in one scenario'],stats:[3,3,3]},
 {id:'reserve',name:['Резерв','Reserve'],tag:['Запас для восстановления','Recovery reserve'],focus:['Понятное окно восстановления','Clear recovery window'],tradeoff:['Меньше мобильности в примере','Less mobility in this illustration'],stats:[2,5,2]},
 {id:'mobility',name:['Манёвр','Mobility'],tag:['Смена позиции','Repositioning'],focus:['Свобода перемещения','Movement flexibility'],tradeoff:['Меньше резерва в примере','Less reserve in this illustration'],stats:[4,2,5]}
];
export const talents=[
 {id:'focus',name:['Фокус','Focus'],group:0},{id:'reserve',name:['Резерв','Reserve'],group:0},{id:'momentum',name:['Темп','Momentum'],group:1},{id:'guard',name:['Опора','Guard'],group:1},{id:'insight',name:['Контекст','Insight'],group:2},{id:'recovery',name:['Восстановление','Recovery'],group:2}
];
export const market=[
 {id:'ore',name:['Образец руды','Ore sample'],price:12,quantity:20,category:['Материал','Material']},
 {id:'cloth',name:['Образец ткани','Cloth sample'],price:7,quantity:40,category:['Материал','Material']},
 {id:'herb',name:['Образец травы','Herb sample'],price:4,quantity:30,category:['Материал','Material']},
 {id:'crystal',name:['Образец кристалла','Crystal sample'],price:24,quantity:5,category:['Компонент','Component']},
 {id:'leather',name:['Образец кожи','Leather sample'],price:9,quantity:15,category:['Материал','Material']},
 {id:'ink',name:['Образец чернил','Ink sample'],price:16,quantity:8,category:['Компонент','Component']}
];
export const quests=[
 {id:'survey',name:['Осмотреть область','Survey the area'],detail:['Проверить описание и условия','Review description and conditions']},
 {id:'collect',name:['Собрать образцы','Collect samples'],detail:['Проверить предметы и количество','Review items and quantity']},
 {id:'return',name:['Вернуться к заказчику','Return to the contact'],detail:['Проверить условия завершения','Review completion requirements']}
];
export const phases={
 prepare:{name:['Подготовка','Preparation'],headline:['Понять исходные условия','Understand the starting conditions'],steps:[['Проверить роль и источник','Review role and source'],['Уточнить версию и ограничения','Check version and limitations'],['Выбрать окно внимания','Choose the attention window']]},
 react:{name:['Реакция','Response'],headline:['Отделить сигнал от предположения','Separate signal from inference'],steps:[['Прочитать состояние источника','Read the source status'],['Проверить давность снимка','Check snapshot age'],['Оставить решение игроку','Leave the decision to the player']]},
 recover:{name:['Восстановление','Recovery'],headline:['Вернуть ясность перед продолжением','Restore clarity before continuing'],steps:[['Остановить наблюдение при отзыве','Stop observation on revocation'],['Восстановить доступ к источнику','Restore source access'],['Явно возобновить наблюдение','Explicitly resume observation']]}
};
export const moduleKinds=['character','builds','talents','pve','pvp','rotations','auction','professions','quests','economy','battle'];
