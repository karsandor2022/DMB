module.exports = {
    name: 'back',
    description: 'Go back to the previous song',
    async execute(client, interaction) {
        if (client.mode === 'LOCAL') {
            const queue = client.player.nodes.get(interaction.guild.id);
            if (!queue || !queue.history.previousTrack) return interaction.reply({ content: "❌ No previous track history.", ephemeral: true });
            
            await queue.history.back();
            return interaction.reply("⏮️ **Playing Previous Track**");
        } else {
            return interaction.reply({ content: "❌ 'Back' function requires advanced queue management not available in basic Remote mode.", ephemeral: true });
        }
    }
};