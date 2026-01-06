module.exports = {
    name: 'volume',
    description: 'Change the current volume level',
    options: [{ name: 'level', type: 4, description: 'Level 1-100', required: true }],
    async execute(client, interaction) {
        const level = interaction.options.getInteger('level');
        if (level < 0 || level > 100) return interaction.reply({ content: "❌ Please choose 1-100.", ephemeral: true });

        if (client.mode === 'LOCAL') {
            const queue = client.player.nodes.get(interaction.guild.id);
            if (queue) queue.node.setVolume(level);
        } else {
            const player = client.shoukaku.getNode().players.get(interaction.guild.id);
            if (player) player.setGlobalVolume(level);
        }
        return interaction.reply(`🔊 Volume changed to **${level}%**`);
    }
};