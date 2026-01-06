module.exports = {
    name: 'skip',
    description: 'Skip to the next song in the queue',
    async execute(client, interaction) {
        if (client.mode === 'LOCAL') {
            const queue = client.player.nodes.get(interaction.guild.id);
            if (!queue || !queue.isPlaying()) return interaction.reply({ content: "❌ Nothing is playing.", ephemeral: true });
            
            queue.node.skip();
            return interaction.reply("⏭️ **Skipped**");
        } else {
            const player = client.shoukaku.getNode().players.get(interaction.guild.id);
            if (!player) return interaction.reply({ content: "❌ Nothing is playing.", ephemeral: true });
            
            player.stopTrack(); // In basic Lavalink implementation, stopping triggers the next song if you have a queue loop
            return interaction.reply("⏭️ **Skipped**");
        }
    }
};