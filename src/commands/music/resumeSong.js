module.exports = {
    name: 'resume',
    description: 'Resume the paused song',
    async execute(client, interaction) {
        if (client.mode === 'LOCAL') {
            const queue = client.player.nodes.get(interaction.guild.id);
            if (!queue) return interaction.reply({ content: "❌ Nothing is playing.", ephemeral: true });
            
            queue.node.resume();
            return interaction.reply("▶️ **Resumed**");
        } else {
            const player = client.shoukaku.getNode().players.get(interaction.guild.id);
            if (!player) return interaction.reply({ content: "❌ Nothing is playing.", ephemeral: true });
            
            player.setPaused(false);
            return interaction.reply("▶️ **Resumed**");
        }
    }
};