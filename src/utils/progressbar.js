module.exports = (current, total, size = 15) => {
    if (!total || total === 0) return '🔘' + '▬'.repeat(size) + ' [Live]';
    const progress = Math.round((size * current) / total);
    const empty = size - progress > 0 ? size - progress : 0;
    
    const bar = '▬'.repeat(progress) + '🔘' + '▬'.repeat(empty);
    
    const fmt = (ms) => {
        const s = Math.floor((ms / 1000) % 60);
        const m = Math.floor((ms / (1000 * 60)) % 60);
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    };
    return `${bar} \`[${fmt(current)}/${fmt(total)}]\``;
};