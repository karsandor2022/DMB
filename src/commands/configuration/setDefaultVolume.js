module.exports = {
    name: 'setdefaultvolume',
    description: '[Config] Set the starting volume (Default: 50%)',
    options: [{ name: 'percentage', type: 4, description: '1-100', required: true }],
    async execute(client, interaction) {
        const vol = interaction.options.getInteger('percentage');
        client.defaultVolume = vol;
        interaction.reply(`🔊 Base Volume set to **${vol}%**`);
    }
};